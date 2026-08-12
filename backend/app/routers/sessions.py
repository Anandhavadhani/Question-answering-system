import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.db import mongo

router = APIRouter()


@router.post("/")
def create_session():
	"""Create a new session document and return its id."""
	session_id = str(uuid.uuid4())
	doc = {"session_id": session_id, "created_at": datetime.utcnow(), "history": []}
	# store in a dedicated collection 'sessions'
	sessions = mongo.db.get_collection("sessions")
	sessions.insert_one(doc)
	return {"session_id": session_id}


@router.get("/{session_id}/history")
def get_history(session_id: str):
	"""Return the history array stored on the session document."""
	sessions = mongo.db.get_collection("sessions")
	s = sessions.find_one({"session_id": session_id})
	if not s:
		raise HTTPException(status_code=404, detail="session not found")
	return {"history": s.get("history", [])}
