# Run command: uvicorn app.main:app --reload --port 8000
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ask, documents, health, sessions

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:5173",
		"http://127.0.0.1:5173",
		"http://localhost:3000",
		"http://127.0.0.1:3000",
		"*",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(ask.router, prefix="/ask", tags=["ask"])
app.include_router(health.router, prefix="/health", tags=["health"])
