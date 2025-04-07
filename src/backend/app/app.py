import os
import logging
import io
from fastapi import FastAPI, Security, HTTPException, Depends, Body, Request, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.status import HTTP_403_FORBIDDEN
from dotenv import load_dotenv
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
import asyncio
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import os
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
import tempfile
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import html
import re

class Message(BaseModel):
    role: str
    content: str

class PDFFile(BaseModel):
    filename: str
    content: str  # Base64 encoded PDF content (will be decoded before processing)

class FinalizeReportRequest(BaseModel):
    messages: List[Message]
    pdf_files: List[PDFFile]
    title: Optional[str] = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Ensure logs are output to the console
    ]
)

# Create logger instance
logger = logging.getLogger(__name__)

# Run local AI model (Ollama)
# model = OpenAIChatCompletionsModel( 
#     model="mistral-small:22b-instruct-2409-fp16",
#     openai_client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key='ollama'),
# )

modelname = 'gpt-4o'

global triage_agent
triage_agent = None
global trafficlaw_agent
trafficlaw_agent = None
global other_agent
other_agent = None
global summary_agent
summary_agent = None
global collection_agent
collection_agent = None

def load_prompt(filename: str, default: str) -> str:
    """
    Load a prompt from a file.
    """
    txtfile = filename + ".txt"
    mdfile = filename + ".md"
    try:
        with open(mdfile, "r", encoding="utf-8") as file:
            logger.info(f"Loaded prompt from {mdfile}")
            return file.read().strip()
    except FileNotFoundError:
        logger.warning(f"{mdfile} not found. Using {txtfile}.")
        try:
            with open(txtfile, "r", encoding="utf-8") as file:
                logger.info(f"Loaded prompt from {txtfile}")
                return file.read().strip()
        except FileNotFoundError:
            logger.warning(f"{filename} not found. Using hardcoded prompt as fallback.")
            return default


# Load agents
def load_agents():
    global triage_agent, trafficlaw_agent, other_agent, summary_agent  # Declare globals

    # Prompts
    triage_prompt = load_prompt("./prompts/triage_prompt", """
    Frage den Benutzer, um was es geht, und versuche den Fall dem korrekten Agenten zuzuordnen.
    Leite nur an den Agenten weiter, wenn du sicher bist, dass es sich um einen Fall handelt, der von einem Agenten bearbeitet werden kann.
    Du darfst keine Fragen beantworten.
    """)

    # Agents
    road_traffic_prompt = load_prompt("./prompts/road_traffic_prompt", """
        Antworte mit "SORRY, Prompt nicht gefunden" und gib den Grund an, warum du nicht helfen kannst.
        """)
    
    trafficlaw_agent = Agent(
        name="Road Traffic Law agent (Speeding)",
        instructions=road_traffic_prompt,
        model=modelname
    )
    
    debt_collection_prompt = load_prompt("./prompts/betreibung_prompt", """
        Antworte mit "SORRY, Prompt nicht gefunden" und gib den Grund an, warum du nicht helfen kannst.
        """)
    
    collection_agent = Agent(
        name="Debt collection agent",
        instructions=debt_collection_prompt,
        model=modelname
    )

    other_agent = Agent(
        name="Other legal field agent (MISC))",
        instructions="You always respond with 'Sorry, I can only help with Road Traffic Law.'",
        model=modelname
    )

    summary_agent = Agent(
        name="Summary agent",
        instructions="Wenn alle Informationen vorliegen, fasse die Informationen zusammen und gib sie zurück und bedanke dich beim Benutzer für die Informationen. Wir werden die Daten nun an die/den zuständige/n Anwätin/Anwalt weiterleiten.",
        model=modelname
    )
    
    triage_agent = Agent(
        name="Triage agent",
        instructions=triage_prompt,
        handoffs=[other_agent, trafficlaw_agent, collection_agent, summary_agent],
        model=modelname
    )
    
# Load agents
load_agents()

# Function to create a PDF cover page using ReportLab
def create_cover_page(title, content, merger):
    """
    Create a cover page using ReportLab
    
    Args:
        title: The title for the cover page
        content: Text content for the cover page
        merger: PyPDF2.PdfMerger object to add the cover page to
    """
    # Create a BytesIO object to store the PDF
    buffer = io.BytesIO()
    
    # Create the PDF document using ReportLab
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=36,
        bottomMargin=72
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Custom styles for the document
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        alignment=1,  # Center alignment
        spaceAfter=15,
        textColor=colors.darkblue
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.darkblue,
        borderWidth=0,
        borderPadding=5,
        borderColor=colors.lightgrey,
        borderRadius=2
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=5
    )
    
    # Container for all flowable elements
    elements = []
    
    # Add the title with better formatting (safely escaped for XML)
    safe_title = html.escape(title)
    elements.append(Paragraph(safe_title, title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Process content by looking for specific sections
    # Extract main sections from the content
    try:
        # Use more robust section detection
        content_parts = {}
        current_section = "INTRO"
        content_parts[current_section] = []
        
        # Split by lines first to handle various formats
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers (all uppercase with colon or just all uppercase)
            if (line.upper() == line and (':' in line or line.endswith(':'))) or line.strip() in ['CASE SUMMARY', 'ATTACHED DOCUMENTS', 'CONVERSATION HISTORY']:
                current_section = line.rstrip(':')
                content_parts[current_section] = []
            else:
                content_parts[current_section].append(line)
        
        # Now process each section with appropriate formatting
        for section, lines in content_parts.items():
            if section != "INTRO":  # Skip the intro section if it's empty
                # Add the section header
                elements.append(Paragraph(section, header_style))
                
                # Special handling for different sections
                if "ATTACHED DOCUMENTS" in section:
                    # Create a simple list of documents
                    for line in lines:
                        if line.strip():
                            # Format document lines as bullets with safe text
                            safe_line = html.escape(line)
                            elements.append(Paragraph("• " + safe_line, normal_style))
                elif "CONVERSATION HISTORY" in section:
                    # Format conversation with role highlighting
                    current_role = None
                    message_text = []
                    
                    # Helper function to escape XML/HTML special characters
                    def escape_xml(text):
                        # Escape XML special chars but preserve <br/> tags
                        text = re.sub(r'<(?!br/?>)', '&lt;', text)
                        text = re.sub(r'(?<!<br/)>', '&gt;', text)
                        text = text.replace('&', '&amp;').replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')
                        return text
                    
                    for line in lines:
                        # Check if a line starts with a role indicator
                        if line.startswith("Client:") or line.startswith("Legal Assistant:"):
                            # If we have accumulated text from a previous role, add it
                            if current_role and message_text:
                                # Process message text for XML safety
                                safe_messages = [escape_xml(msg) for msg in message_text]
                                msg_text = "<br/>".join(safe_messages)
                                
                                # Safe role name
                                safe_role = html.escape(current_role)
                                
                                # Add the role as a bold header
                                elements.append(Paragraph(f"<b>{safe_role}</b>", normal_style))
                                # Add the message content
                                elements.append(Paragraph(msg_text, normal_style))
                                elements.append(Spacer(1, 0.1*inch))
                                message_text = []
                            
                            # Update current role
                            current_role = line
                        else:
                            # Accumulate message text
                            if current_role:  # Only add if we have a role
                                message_text.append(line)
                    
                    # Add the last message if there is one
                    if current_role and message_text:
                        # Process message text for XML safety
                        safe_messages = [escape_xml(msg) for msg in message_text]
                        msg_text = "<br/>".join(safe_messages)
                        
                        # Safe role name
                        safe_role = html.escape(current_role)
                        
                        # Add the role as a bold header
                        elements.append(Paragraph(f"<b>{safe_role}</b>", normal_style))
                        # Add the message content
                        elements.append(Paragraph(msg_text, normal_style))
                else:
                    # Default handling for other sections (with safe escaping)
                    combined_text = " ".join(lines)
                    safe_text = html.escape(combined_text)
                    elements.append(Paragraph(safe_text, normal_style))
                
                elements.append(Spacer(1, 0.15*inch))
    except Exception as e:
        # Fallback method if the section extraction fails
        logger.error(f"Error formatting cover page content: {str(e)}")
        
        # Simple fallback - just add the content as is but safely escaped
        elements.append(Paragraph("Content:", header_style))
        
        # Function to escape content safely for XML
        def safe_escape(text):
            return html.escape(text).replace('\n', '<br/>')
        
        # Add each line as a separate paragraph with proper escaping
        for line in content.split('\n'):
            if line.strip():
                elements.append(Paragraph(safe_escape(line), normal_style))
    
    # Build the PDF
    try:
        doc.build(elements)
        
        # Get the PDF data from the BytesIO object
        buffer.seek(0)
        
        # Add the cover page to the merger
        merger.append(buffer)
    except Exception as e:
        logger.error(f"Error building cover page: {str(e)}")
        
        # Emergency fallback - create a very simple cover page
        # Create new buffer and document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Safe version of everything
        try:
            safe_title = html.escape(title)
            
            # Create the absolute simplest document possible
            elements = [
                Paragraph(safe_title, styles['Title']),
                Spacer(1, 0.25*inch),
                Paragraph("Error creating formatted cover page. Please see the attached documents.", styles['Normal'])
            ]
            
            # Try to build it
            doc.build(elements)
            buffer.seek(0)
            merger.append(buffer)
            
            logger.info("Successfully created emergency fallback cover page")
        except Exception as final_error:
            # Absolute last resort - add a blank page with no content
            logger.error(f"Emergency fallback failed: {str(final_error)}. Adding blank page instead.")
            blank_writer = PyPDF2.PdfWriter()
            blank_writer.add_blank_page(width=612, height=792)  # US Letter size
            blank_buffer = io.BytesIO()
            blank_writer.write(blank_buffer)
            blank_buffer.seek(0)
            merger.append(blank_buffer)

# Run Agent
async def main(message_history: List[Message]):
    # Convert Message objects to dictionaries
    formatted_messages = [{"role": msg.role, "content": msg.content} for msg in message_history]
    result = await Runner.run(triage_agent, input=formatted_messages)
    logger.info(result.final_output)
    return result.final_output

# Load environment variables from .env file
load_dotenv()

API_KEY = os.environ.get("CLIENT_API_KEY")
security = HTTPBearer(auto_error=False)

async def get_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="API key not configured"
        )
    if not credentials:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Bearer authentication required"
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Bearer authentication required"
        )
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Invalid API key"
        )
    return credentials.credentials

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    return {"message": "Hello world!"}

@app.get("/secured")
async def secured_endpoint(api_key: str = Depends(get_api_key)):
    return {"message": "This is a secured endpoint"}

@app.post("/agent")
async def agent_endpoint(
    request: Request,
    api_key: str = Depends(get_api_key), 
    message_history: List[Message] = Body(...)
):  
    # Log the raw request body for debugging
    body = await request.body()
    logger.info("RAW REQUEST BODY:")
    logger.info(body.decode())
    logger.info("#" * 50)
    
    logger.info("Received message history:")
    logger.info("#" * 50)
    logger.info(message_history)
    logger.info("#" * 50)
    for message in message_history:
        logger.info(f"{message.role}: {message.content}")
    logger.info("#" * 50)
    return await main(message_history)

@app.post("/reload-prompts")
async def reload_prompts(api_key: str = Depends(get_api_key)):
    # Reload agents
    load_agents()

    return {"message": "Prompts reloaded successfully"}

@app.post("/parse-document")
async def parse_document(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    """
    Parse a document using unstructured and return the extracted text.
    Supports PDF and DOCX formats.
    """
    # Get the form data using FastAPI's form handling
    form_data = await request.form()
    
    # Check if a file was uploaded
    if "file" not in form_data:
        return {"error": "No file uploaded"}
    
    file = form_data["file"]
    
    # Create a temporary file to save the uploaded file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        # Write the content of the uploaded file to the temporary file
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Get the file extension
        file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
        
        # Parse the document based on its type
        if file_extension == 'pdf':
            elements = partition_pdf(filename=temp_file_path)
        elif file_extension in ['docx', 'doc']:
            elements = partition_docx(filename=temp_file_path)
        else:
            os.unlink(temp_file_path)  # Clean up the temporary file
            return {"error": f"Unsupported file format: {file_extension}. Supported formats are PDF and DOCX."}
        
        # Convert all elements to text and join them
        text = "\n".join([str(element) for element in elements])
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "text": text
        }
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        return {"error": f"Failed to parse document: {str(e)}"}
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

@app.post("/finalize-report")
async def finalize_report(request: FinalizeReportRequest, api_key: str = Depends(get_api_key)):
    """
    Combine multiple PDF files into a single report with a summary cover page.
    
    Parameters:
    - messages: Chat history for summarization
    - pdf_files: List of PDF files (filename and base64-encoded content)
    - title: Optional title for the report
    
    Returns:
    - A combined PDF document
    """
    try:
        # Validate that PDF content is not empty
        for pdf_file in request.pdf_files:
            if not pdf_file.content:
                raise HTTPException(
                    status_code=400, 
                    detail=f"PDF file {pdf_file.filename} has empty content"
                )
            logger.info(f"PDF file {pdf_file.filename} content length: {len(pdf_file.content)}")
        # Create a PDF merger object
        merger = PyPDF2.PdfMerger()
        
        # Generate a more meaningful summary using the AI model
        try:
            # Create a prompt for summarization
            summary_prompt = f"""
            Du bist ein juristischer Dokumentenzusammenfasser. Du sollst ein Gespräch zwischen einem Mandanten und einem Assistenten zusammenfassen.
            Erstelle eine professionelle, prägnante Zusammenfassung der Hauptthemen, Fragen und gegebenen Ratschläge in diesem Gespräch.
            Konzentriere dich darauf, die Art des rechtlichen Falls und die wichtigsten rechtlichen Punkte zu identifizieren.
            
            Sei sachlich, objektiv und vermeide Spekulationen. Halte deine Zusammenfassung auf 2-4 Sätze beschränkt.
            """
            
            # Convert message history to a format suitable for the summary agent
            formatted_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            # Add the summary prompt as a system message
            prompt_message = {"role": "system", "content": summary_prompt}
            summary_messages = [prompt_message] + formatted_messages
            
            # Use the OpenAI model to generate a summary
            from openai import AsyncOpenAI
            
            # Create client with API key from environment or default configuration
            client = AsyncOpenAI()
            
            # Generate summary
            summary_response = await client.chat.completions.create(
                model=modelname,  # Using the same model defined earlier in the file
                messages=summary_messages,
                max_tokens=350
            )
            
            # Extract the summary
            ai_summary = summary_response.choices[0].message.content.strip()
            logger.info(f"Generated AI summary: {ai_summary}")
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            # Fallback to a basic summary if AI generation fails
            ai_summary = "Unable to generate AI summary. This report contains a conversation related to legal matters."
        
        # Create a formatted message history
        message_history = "Full Conversation:\n\n"
        for i, msg in enumerate(request.messages, 1):
            role_display = "Client" if msg.role == "user" else "Legal Assistant"
            message_history += f"{i}. {role_display}:\n{msg.content}\n\n"
        
        # Create a list of attached documents
        attached_docs = "Attached Documents:\n"
        for i, pdf_file in enumerate(request.pdf_files, 1):
            attached_docs += f"{i}. {pdf_file.filename}\n"
        
        # Set the title
        report_title = request.title or "Legal Case Documents"
        
        # Format the cover page content
        cover_content = f"""
{report_title}

CASE SUMMARY:
{ai_summary}

ATTACHED DOCUMENTS:
{"".join(f"{i}. {pdf_file.filename}\n" for i, pdf_file in enumerate(request.pdf_files, 1))}

CONVERSATION HISTORY:
"""
        # Add each message with proper formatting and ensure line breaks are preserved
        for msg in request.messages:
            role_display = "Client" if msg.role == "user" else "Legal Assistant"
            # Add the role as a prefix
            cover_content += f"{role_display}:\n"
            # Add the message content with preserved line breaks
            cover_content += f"{msg.content}\n\n"
        
        # Log the cover content for debugging
        logger.info(f"Cover page content: {cover_content[:500]}...")
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_text:
            temp_text.write(cover_content.encode('utf-8'))
            temp_text_path = temp_text.name
        
        try:
            # Create and add a cover page with content
            create_cover_page(report_title, cover_content, merger)
            
            # Log that we've added the cover page
            logger.info("Added cover page to PDF")
            
            # Also write the cover content to a separate text file for manual reference
            with open("cover_page_content.txt", "w", encoding="utf-8") as cover_file:
                cover_file.write(cover_content)
                logger.info("Saved cover page content to cover_page_content.txt for reference")
        finally:
            # Clean up the temporary text file
            os.unlink(temp_text_path)
        
        # Add all PDF files in the order they were provided
        for pdf_file in request.pdf_files:
            try:
                # Create a temporary file for each PDF
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                    # PDF files should be binary data, not text
                    # Check if content is base64 encoded and decode if needed
                    import base64
                    try:
                        # Try to decode if it's base64 encoded
                        if isinstance(pdf_file.content, str):
                            try:
                                pdf_content = base64.b64decode(pdf_file.content)
                            except base64.binascii.Error:
                                logger.error(f"Invalid base64 content in {pdf_file.filename}")
                                raise ValueError(f"Invalid PDF content: {pdf_file.filename} contains invalid base64 data")
                        else:
                            pdf_content = pdf_file.content
                        
                        # Write the binary content to the temporary file
                        temp_pdf.write(pdf_content)
                        temp_pdf_path = temp_pdf.name
                        logger.info(f"Successfully wrote PDF file {pdf_file.filename} to temporary file")
                    except Exception as e:
                        logger.error(f"Error processing PDF content for {pdf_file.filename}: {str(e)}")
                        raise
                
                # Validate that the PDF is readable before adding it to the merger
                try:
                    # Try to read the PDF to make sure it's valid
                    with open(temp_pdf_path, "rb") as test_pdf:
                        reader = PyPDF2.PdfReader(test_pdf)
                        # Check if PDF has pages
                        if len(reader.pages) == 0:
                            logger.warning(f"PDF file {pdf_file.filename} has 0 pages")
                        else:
                            logger.info(f"PDF file {pdf_file.filename} has {len(reader.pages)} pages")
                    
                    # If we got here, the PDF is valid, so add it to the merger
                    merger.append(temp_pdf_path)
                except PyPDF2.errors.PdfReadError as e:
                    logger.warning(f"Attempting to repair corrupted PDF file {pdf_file.filename}: {str(e)}")
                    try:
                        # Attempt to repair the corrupted PDF
                        repaired_pdf = io.BytesIO()
                        with open(temp_pdf_path, "rb") as corrupted_file:
                            reader = PyPDF2.PdfReader(corrupted_file)
                            writer = PyPDF2.PdfWriter()
                            for page in reader.pages:
                                writer.add_page(page)
                            writer.write(repaired_pdf)
                        repaired_pdf.seek(0)
                        merger.append(repaired_pdf)
                        logger.info(f"Successfully repaired and included {pdf_file.filename}")
                    except Exception as repair_error:
                        logger.error(f"Failed to repair PDF file {pdf_file.filename}: {str(repair_error)}")
                        # Add a placeholder page indicating the file could not be processed
                        placeholder_writer = PyPDF2.PdfWriter()
                        placeholder_writer.add_blank_page(width=612, height=792)  # US Letter size
                        placeholder_stream = io.BytesIO()
                        placeholder_writer.write(placeholder_stream)
                        placeholder_stream.seek(0)
                        merger.append(placeholder_stream)
                        logger.warning(f"Added placeholder for {pdf_file.filename}")
                finally:
                    # Make sure to clean up each temporary file
                    os.unlink(temp_pdf_path)
            except Exception as e:
                logger.error(f"Error processing PDF file {pdf_file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error processing PDF file {pdf_file.filename}: {str(e)}"
                )
        
        # Write the combined PDF to a BytesIO object
        merged_pdf = io.BytesIO()
        merger.write(merged_pdf)
        merger.close()
        merged_pdf.seek(0)
        
        # Create a temporary reference to the cover file path
        cover_file_path = os.path.join(os.path.dirname(__file__), "cover_page_content.txt")
        
        # Define a cleanup function that will run after the response is delivered
        async def cleanup_after_response():
            # Wait a moment to ensure file is not in use
            await asyncio.sleep(1)
            try:
                # Remove the cover page content file if it exists
                if os.path.exists(cover_file_path):
                    os.remove(cover_file_path)
                    logger.info("Cleaned up cover_page_content.txt file")
            except Exception as e:
                logger.error(f"Error cleaning up cover page file: {str(e)}")
        
        # Schedule the cleanup to run in the background
        asyncio.create_task(cleanup_after_response())
        
        # Return the combined PDF as a streaming response
        return StreamingResponse(
            merged_pdf, 
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="combined_report.pdf"'
            }
        )
    
    except Exception as e:
        logger.error(f"Error finalizing report: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error finalizing report: {str(e)}"
        )

@app.post("/finalize-report-form")
async def finalize_report_form(
    request: Request,
    title: Optional[str] = Form(None),
    messages: str = Form(...),  # JSON string of messages
    files: List[UploadFile] = File(...),
    api_key: str = Depends(get_api_key)
):
    """
    Alternate version of finalize-report endpoint that accepts multipart/form-data
    with actual file uploads instead of base64 encoded content.
    
    Parameters:
    - title: Optional title for the report
    - messages: JSON string representing chat messages
    - files: List of uploaded PDF files
    
    Returns:
    - A combined PDF document
    """
    try:
        # Parse the messages JSON string
        import json
        message_list = json.loads(messages)
        parsed_messages = [Message(**msg) for msg in message_list]
        
        # Create a PDF merger object
        merger = PyPDF2.PdfMerger()
        
        # Generate a more meaningful summary using the AI model
        try:
            # Create a prompt for summarization
            summary_prompt = f"""
            Du bist ein juristischer Dokumentenzusammenfasser. Du sollst ein Gespräch zwischen einem Mandanten und einem Assistenten zusammenfassen.
            Erstelle eine professionelle, prägnante Zusammenfassung der Hauptthemen, Fragen und gegebenen Ratschläge in diesem Gespräch.
            Konzentriere dich darauf, die Art des rechtlichen Falls und die wichtigsten rechtlichen Punkte zu identifizieren.
            
            Sei sachlich, objektiv und vermeide Spekulationen. Halte deine Zusammenfassung auf 2-4 Sätze beschränkt.
            """
            
            # Convert message history to a format suitable for the summary agent
            formatted_messages = [{"role": msg.role, "content": msg.content} for msg in parsed_messages]
            
            # Add the summary prompt as a system message
            prompt_message = {"role": "system", "content": summary_prompt}
            summary_messages = [prompt_message] + formatted_messages
            
            # Use the OpenAI model to generate a summary
            from openai import AsyncOpenAI
            
            # Create client with API key from environment or default configuration
            client = AsyncOpenAI()
            
            # Generate summary
            summary_response = await client.chat.completions.create(
                model=modelname,  # Using the same model defined earlier in the file
                messages=summary_messages,
                max_tokens=350
            )
            
            # Extract the summary
            ai_summary = summary_response.choices[0].message.content.strip()
            logger.info(f"Generated AI summary: {ai_summary}")
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            # Fallback to a basic summary if AI generation fails
            ai_summary = "Unable to generate AI summary. This report contains a conversation related to legal matters."
        
        # Create a formatted message history
        message_history = "Full Conversation:\n\n"
        for i, msg in enumerate(parsed_messages, 1):
            role_display = "Client" if msg.role == "user" else "Legal Assistant"
            message_history += f"{i}. {role_display}:\n{msg.content}\n\n"
        
        # Create a list of attached documents
        attached_docs = "Attached Documents:\n"
        for i, file in enumerate(files, 1):
            attached_docs += f"{i}. {file.filename}\n"
        
        # Set the title
        report_title = title or "Legal Case Documents"
        
        # Format the cover page content
        cover_content = f"""
{report_title}

CASE SUMMARY:
{ai_summary}

ATTACHED DOCUMENTS:
{"".join(f"{i}. {file.filename}\n" for i, file in enumerate(files, 1))}

CONVERSATION HISTORY:
"""
        # Add each message with proper formatting and ensure line breaks are preserved
        for msg in parsed_messages:
            role_display = "Client" if msg.role == "user" else "Legal Assistant"
            # Add the role as a prefix
            cover_content += f"{role_display}:\n"
            # Add the message content with preserved line breaks
            cover_content += f"{msg.content}\n\n"
        
        # Log the cover content for debugging
        logger.info(f"Cover page content: {cover_content[:500]}...")
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_text:
            temp_text.write(cover_content.encode('utf-8'))
            temp_text_path = temp_text.name
        
        try:
            # Create and add a cover page with content
            create_cover_page(report_title, cover_content, merger)
            
            # Log that we've added the cover page
            logger.info("Added cover page to PDF")
            
            # Also write the cover content to a separate text file for manual reference
            with open("cover_page_content.txt", "w", encoding="utf-8") as cover_file:
                cover_file.write(cover_content)
                logger.info("Saved cover page content to cover_page_content.txt for reference")
        finally:
            # Clean up the temporary text file
            os.unlink(temp_text_path)
        
        # Add all PDF files in the order they were provided
        for file in files:
            try:
                # Read the file content
                content = await file.read()
                
                # Validate PDF content is not empty
                if not content:
                    raise ValueError(f"PDF file {file.filename} has empty content")
                
                logger.info(f"PDF file {file.filename} content length: {len(content)}")
                
                # Create a temporary file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                    temp_pdf.write(content)
                    temp_pdf_path = temp_pdf.name
                    logger.info(f"Successfully wrote PDF file {file.filename} to temporary file")
                
                # Validate that the PDF is readable before adding it to the merger
                try:
                    # Try to read the PDF to make sure it's valid
                    with open(temp_pdf_path, "rb") as test_pdf:
                        reader = PyPDF2.PdfReader(test_pdf)
                        # Check if PDF has pages
                        if len(reader.pages) == 0:
                            logger.warning(f"PDF file {file.filename} has 0 pages")
                        else:
                            logger.info(f"PDF file {file.filename} has {len(reader.pages)} pages")
                    
                    # If we got here, the PDF is valid, so add it to the merger
                    merger.append(temp_pdf_path)
                except PyPDF2.errors.PdfReadError as e:
                    logger.warning(f"PDF read error for file {file.filename}: {str(e)}")
                    placeholder_writer = PyPDF2.PdfWriter()
                    placeholder_writer.add_blank_page(width=612, height=792)  # US Letter size
                    placeholder_stream = io.BytesIO()
                    placeholder_writer.write(placeholder_stream)
                    placeholder_stream.seek(0)
                    merger.append(placeholder_stream)
                    logger.warning(f"Added placeholder for {file.filename}")
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_pdf_path)
                    
            except Exception as e:
                logger.error(f"Error processing PDF file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error processing PDF file {file.filename}: {str(e)}"
                )
        
        # Write the combined PDF to a BytesIO object
        merged_pdf = io.BytesIO()
        merger.write(merged_pdf)
        merger.close()
        merged_pdf.seek(0)
        
        # Create a temporary reference to the cover file path
        cover_file_path = os.path.join(os.path.dirname(__file__), "cover_page_content.txt")
        
        # Define a cleanup function that will run after the response is delivered
        async def cleanup_after_response():
            # Wait a moment to ensure file is not in use
            await asyncio.sleep(1)
            try:
                # Remove the cover page content file if it exists
                if os.path.exists(cover_file_path):
                    os.remove(cover_file_path)
                    logger.info("Cleaned up cover_page_content.txt file")
            except Exception as e:
                logger.error(f"Error cleaning up cover page file: {str(e)}")
        
        # Schedule the cleanup to run in the background
        asyncio.create_task(cleanup_after_response())
        
        # Return the combined PDF as a streaming response
        return StreamingResponse(
            merged_pdf, 
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="combined_report.pdf"'
            }
        )
    
    except Exception as e:
        logger.error(f"Error finalizing report (form): {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error finalizing report: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)