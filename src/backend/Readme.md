# Docker Backend

## Overview
This is a FastAPI-based backend service that provides conversational AI agents for legal assistance, with a focus on Road Traffic Law. The application uses agents powered by local AI models (Ollama) to triage and handle different types of legal inquiries.

## Setup and Installation

### Prerequisites
- Docker (for containerized deployment)
- Python 3.8+ (for local development)
- Ollama running locally (for using local AI models)

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app/app.py
```

## Docker Deployment

### Production
Set OPENAI_API_KEY and CLIENT_API_KEY as environment variables in the docker run command!

```bash
docker build -t backend .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_api_key -e CLIENT_API_KEY=your_client_api_key backend
```

### Development with Hot-Reloading
For development with hot-reloading (automatically reloads when code changes):

```bash
# Build the development image
docker build -t backend-dev .

# Run with the app folder mounted as a volume for hot-reloading
docker run -p 8000:8000 -e OPENAI_API_KEY=your_api_key -e CLIENT_API_KEY=your_client_api_key -v $(pwd)/app:/app/app backend-dev
```

## API Documentation

### Endpoints

| Endpoint | Method | Authentication | Description |
|----------|--------|----------------|-------------|
| `/` | GET | None | Health check endpoint |
| `/secured` | GET | Required | Test endpoint for authenticated requests |
| `/agent` | POST | Required | Submit messages to AI agents |

### Authentication
Protected endpoints require Bearer token authentication with the CLIENT_API_KEY value:

```bash
curl -H "Authorization: Bearer your_client_api_key" http://localhost:8000/secured
```

Public endpoints (like the root endpoint) don't require authentication.

### Agent Endpoint
The `/agent` endpoint accepts a list of message objects with the following structure:

```json
{
  "message_history": [
    {
      "role": "user",
      "content": "Ich wurde geblitzt, was soll ich tun?"
    }
  ]
}
```

## Agent Structure
The backend implements three agents:
- **Triage Agent**: Routes inquiries to the appropriate specialized agent
- **Road Traffic Law Agent**: Handles speeding and traffic-related cases
- **Miscellaneous Legal Agent**: Handles other legal fields (currently limited functionality)
