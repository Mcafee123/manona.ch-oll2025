import os
from fastapi import FastAPI, Security, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_403_FORBIDDEN
from dotenv import load_dotenv
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
import asyncio

model = OpenAIChatCompletionsModel( 
    model="llama3.1",
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
    instructions="You answer in the distinct speaking style of a pirate adding a 'wroom wroom' sound to your answers.",
    model=model
)

triage_agent = Agent(
    name="Triage agent",
    instructions="Handoff to the appropriate specialist agent based on the legal field.",
    handoffs=[spanish_agent, english_agent],
    model=model
)

# Run Agent
async def main():
    result = await Runner.run(triage_agent, input="Ich möchte ein Bier kaufen.")
    print(result.final_output)
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

@app.get("/")
async def root():
    return {"message": "Hello world!"}

@app.get("/secured")
async def secured_endpoint(api_key: str = Depends(get_api_key)):
    return {"message": "This is a secured endpoint"}

@app.get("/agent")
async def agent_endpoint(api_key: str = Depends(get_api_key)):
    return await main()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)