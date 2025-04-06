# manona.ch-oll2025

Frontend: VueJS
Backend: Python + Docker


curl -X POST "http://localhost:8000/agent" \
-H "Authorization: Bearer YOUR_API_KEY" \
-H "Content-Type: application/json" \
-d '[
  {"role": "user", "content": "What is the speed limit in a residential area?"},
]'