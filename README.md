# manona.ch-oll2025

Frontend: VueJS
Backend: Python + Docker

Backend URL (temporary, until api.manona.ch is ready):  https://manona-backend.livelytree-7b4ab806.switzerlandnorth.azurecontainerapps.io
Frontend URL (temporary, until manona.ch is ready):     https://manona-frontend.livelytree-7b4ab806.switzerlandnorth.azurecontainerapps.io/

curl -X POST "http://localhost:8000/agent" \
-H "Authorization: Bearer your_client_api_key" \
-H "Content-Type: application/json" \
-d '[
  {"role": "user", "content": "What is the speed limit in a residential area?"}
]'
