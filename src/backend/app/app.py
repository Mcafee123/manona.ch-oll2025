import os
import logging
from fastapi import FastAPI, Security, HTTPException, Depends, Body, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
from dotenv import load_dotenv
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
import asyncio
from typing import List, Dict
from pydantic import BaseModel
import os
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
import tempfile

class Message(BaseModel):
    role: str
    content: str

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)