# Docker Backend

## Production
Set OPENAI_API_KEY and CLIENT_API_KEY as environment variables in the docker run command!

```bash
docker build -t backend .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_api_key -e CLIENT_API_KEY=your_client_api_key backend
```

## Development with Hot-Reloading
For development with hot-reloading (automatically reloads when code changes):

```bash
# Build the development image
docker build -t backend-dev .

# Run with the app folder mounted as a volume for hot-reloading
docker run -p 8000:8000 -e OPENAI_API_KEY=your_api_key -e CLIENT_API_KEY=your_client_api_key -v $(pwd)/app:/app/app backend-dev
```

## API Authentication

Protected endpoints require Bearer token authentication with the CLIENT_API_KEY value:

```
curl -H "Authorization: Bearer your_client_api_key" http://localhost:8000/secured
```

Public endpoints (like the root endpoint) don't require authentication.
