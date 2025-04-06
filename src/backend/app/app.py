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
model = OpenAIChatCompletionsModel( 
    model="mistral-small:22b-instruct-2409-fp16",
    openai_client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key='ollama'),
)

# Agents
spanish_agent = Agent(
    name="Other legal field agent (MISC))",
    instructions="You always respond with 'Sorry, I can only help with Road Traffic Law.'",
    model=model
)

english_agent = Agent(
    name="Road Traffic Law agent (Speeding)",
    instructions="""
    Deine Aufgabe ist es, Antworten auf die folgenden Fragen zu sammeln:
    #GOAL: Alle Dokumente zu erhalten und Persönliche Informationen über den folgenden Fall.
    #USE CASE Strafbefehl/Busse Strassenverkehr
    #Frage 1: (Personalien) Name, Geburtsdatum, Führerausweis 
    #Frage 2: Was ist passiert? (Nur Blitzerfälle)
    #Frage 3: Beleg: Hast du ein Dokument erhalten? 
        #Var 1: nichts -> nicht genügend Informationen
        #Var 2: Rechnung/Busse 
        #Var 3: Starfbefehl
        #Var 4: Vorladung
    #Frage 4: Wann und wo (Strasse) wurdest du geblitzt? (Um Abweichungen festzustellen)
    #Frage 5: Wer ist der Halter des Fahrzeuges?
        #Var 1: Ich (der jetzt chattet) >>> *Fahrzeugausweis?*
        #Var 2: jemand anderes >>> *Wer?* 
    #Frage 6: Was ist dein Anliegen?
        #Var 1: Willst du die Strafe anfechten?
            #SubVar 1: Anfechten weil: ich nicht gefahren >>> *Foto; falls vorhanden?* 
            #SubVar 2: Anfechten weil: Messung war falsch >>> *Hast du Beweise dafür?*
            #SubVar 3: Anfechten weil: es war ein Notfall >>> *Hast du Beweise dafür?*
        #Var 2: Ich möchte wissen, ob mein Führerausweis entzogen wird
            #SubVar 1: Vorherige Administrativmassnahmen angeordnet >>> *Dokument*
            #SubVar 2: keine Administrativverfahren
            #SubVar 3: Wird das Fahrzeug beruflich benötigt? >>> *Hast du Beweise dafür?*
    """,
    model=model
)

triage_agent = Agent(
    name="Triage agent",
    instructions="""
    Frage den Benutzer, um was es geht, und versuche den Fall dem korrekten Agenten zuzuordnen.
    Leite nur an den Agenten weiter, wenn du sicher bist, dass es sich um einen Fall handelt, der von einem Agenten bearbeitet werden kann.
    Du darfst keine Fragen beantworten.
    """,
    handoffs=[spanish_agent, english_agent],
    model=model
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)