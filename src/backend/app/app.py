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
        
        # Generate a summary of the conversation
        summary = "Chat Summary:\n"
        for msg in request.messages:
            if msg.role == "user":
                summary += f"- User: {msg.content[:100]}...\n"
            elif msg.role == "assistant":
                summary += f"- Assistant: {msg.content[:100]}...\n"
                
        # Create a list of attached documents
        attached_docs = "Attached Documents:\n"
        for i, pdf_file in enumerate(request.pdf_files, 1):
            attached_docs += f"{i}. {pdf_file.filename}\n"
            
        # Set the title
        report_title = request.title or "Combined Legal Documents"
        
        # We need to create a simple first page with the summary
        # For now, we'll create a text file with the summary and convert it to PDF
        # using an external tool or another PDF library in a real implementation
        
        # For this implementation, we'll create a simple PDF directly
        cover_page_content = f"""
        {report_title}
        
        {summary}
        
        {attached_docs}
        """
        
        # Create a temporary first page PDF using PyPDF2
        cover_writer = PyPDF2.PdfWriter()
        # Add a blank page - in a real implementation we would write text to this
        cover_writer.add_blank_page(width=612, height=792)  # US Letter size
        
        # Write the cover page to a stream
        cover_stream = io.BytesIO()
        cover_writer.write(cover_stream)
        cover_stream.seek(0)
        
        # Add the cover page as the first page in the merged document
        merger.append(cover_stream)
        
        # For now, log the cover page content that would be included
        logger.info(f"Cover page content: {cover_page_content}")
        
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
        
        # Generate a summary of the conversation
        summary = "Chat Summary:\n"
        for msg in parsed_messages:
            if msg.role == "user":
                summary += f"- User: {msg.content[:100]}...\n"
            elif msg.role == "assistant":
                summary += f"- Assistant: {msg.content[:100]}...\n"
                
        # Create a list of attached documents
        attached_docs = "Attached Documents:\n"
        for i, file in enumerate(files, 1):
            attached_docs += f"{i}. {file.filename}\n"
            
        # Set the title
        report_title = title or "Combined Legal Documents"
        
        # Create a simple first page with the summary
        cover_page_content = f"""
        {report_title}
        
        {summary}
        
        {attached_docs}
        """
        
        # Create a temporary first page PDF
        cover_writer = PyPDF2.PdfWriter()
        cover_writer.add_blank_page(width=612, height=792)  # US Letter size
        
        # Write the cover page to a stream
        cover_stream = io.BytesIO()
        cover_writer.write(cover_stream)
        cover_stream.seek(0)
        
        # Add the cover page as the first page in the merged document
        merger.append(cover_stream)
        
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