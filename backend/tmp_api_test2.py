from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import only the routers we need to test
from app.routers import sessions, ask

# Monkeypatch embedding to avoid heavy model loads
import app.pipeline.embedding as emb
emb.embed_texts = lambda texts: [[0.0] * 768]

app = FastAPI()
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(ask.router, prefix="/ask", tags=["ask"])

client = TestClient(app)

print('POST /sessions ->')
r = client.post('/sessions/')
print(r.status_code, r.json())

session_id = r.json().get('session_id')
print('\nPOST /ask ->')
r2 = client.post('/ask/', json={
    'session_id': session_id,
    'doc_id': 'example-doc',
    'question': 'What is the total in the table on page 2?'
})
print(r2.status_code, r2.json())

print('\nGET /sessions/{session_id}/history ->')
r3 = client.get(f'/sessions/{session_id}/history')
print(r3.status_code, r3.json())
