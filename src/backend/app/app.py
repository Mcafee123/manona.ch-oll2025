import os
import logging
from fastapi import FastAPI, Security, HTTPException, Depends, Body, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
from dotenv import load_dotenv
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
import asyncio
from typing import List
from pydantic import BaseModel
import os

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

# Agents
spanish_agent = Agent(
    name="Other legal field agent (MISC))",
    instructions="You always respond with 'Sorry, I can only help with Road Traffic Law.'",
    model='gpt-4o-mini'
)

road_traffic_prompt = None

# Load road traffic prompt from file
try:
    with open("./prompts/road_traffic_prompt.txt", "r", encoding="utf-8") as file:
        road_traffic_prompt = file.read().strip()
except FileNotFoundError:
    logger.warning("road_traffic_prompt.txt not found. Using hardcoded road traffic prompt as fallback.")

# Fall back to hardcoded prompt if file loading fails
if not road_traffic_prompt:
    road_traffic_prompt = """Antworte mit "SORRY, Prompt nicht gefunden" und gib den Grund an, warum du nicht helfen kannst."""
    logger.warning("Using hardcoded road traffic prompt as fallback")

english_agent = Agent(
    name="Road Traffic Law agent (Speeding)",
    instructions=road_traffic_prompt,
    model='gpt-4o-mini'
)

triage_prompt = None

# Load triage prompt from file
try:
    with open("./prompts/triage_prompt.txt", "r", encoding="utf-8") as file:
        triage_prompt = file.read().strip()
except FileNotFoundError:
    logger.warning("triage_prompt.txt not found. Using hardcoded triage prompt as fallback.")

# Fall back to hardcoded prompt if file loading fails
if not triage_prompt:
    triage_prompt = """
    Frage den Benutzer, um was es geht, und versuche den Fall dem korrekten Agenten zuzuordnen.
    Leite nur an den Agenten weiter, wenn du sicher bist, dass es sich um einen Fall handelt, der von einem Agenten bearbeitet werden kann.
    Du darfst keine Fragen beantworten.
    """
    logger.warning("Using hardcoded triage prompt as fallback")

triage_agent = Agent(
    name="Triage agent",
    instructions=triage_prompt,
    handoffs=[spanish_agent, english_agent],
    model='gpt-4o-mini'
)

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
    global road_traffic_prompt, triage_prompt, english_agent, triage_agent

    # Reload road traffic prompt
    try:
        with open("./prompts/road_traffic_prompt.txt", "r", encoding="utf-8") as file:
            road_traffic_prompt = file.read().strip()
        logger.info("road_traffic_prompt.txt reloaded successfully.")
    except FileNotFoundError:
        road_traffic_prompt = """Antworte mit "SORRY, Prompt nicht gefunden" und gib den Grund an, warum du nicht helfen kannst."""
        logger.warning("road_traffic_prompt.txt not found. Using hardcoded road traffic prompt as fallback.")

    # Reload triage prompt
    try:
        with open("./prompts/triage_prompt.txt", "r", encoding="utf-8") as file:
            triage_prompt = file.read().strip()
        logger.info("triage_prompt.txt reloaded successfully.")
    except FileNotFoundError:
        triage_prompt = """
        Frage den Benutzer, um was es geht, und versuche den Fall dem korrekten Agenten zuzuordnen.
        Leite nur an den Agenten weiter, wenn du sicher bist, dass es sich um einen Fall handelt, der von einem Agenten bearbeitet werden kann.
        Du darfst keine Fragen beantworten.
        """
        logger.warning("triage_prompt.txt not found. Using hardcoded triage prompt as fallback.")

    # Update agents with reloaded prompts
    english_agent.instructions = road_traffic_prompt
    triage_agent.instructions = triage_prompt

    return {"message": "Prompts reloaded successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)