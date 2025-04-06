# manona.ch-oll2025

Frontend: VueJS
Backend: Python + Docker


curl -X POST "http://localhost:8000/agent" \
-H "Authorization: Bearer your_client_api_key" \
-H "Content-Type: application/json" \
-d '[
  {"role": "user", "content": "What is the speed limit in a residential area?"}
]'