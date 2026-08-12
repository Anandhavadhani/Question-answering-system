import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.pipeline import embedding as embed_module
from app.pipeline import query_rewrite
from app.pipeline import retrieval
from app.pipeline import answer as answer_module
from app.db import mongo

LOGGER = logging.getLogger(__name__)
router = APIRouter()


class AskRequest(BaseModel):
	session_id: str
	question: str
	doc_id: Optional[str] = None
	user_id: Optional[str] = None


@router.post("/")
def ask(req: AskRequest):
	sessions = mongo.db.get_collection("sessions")
	session = sessions.find_one({"session_id": req.session_id}, {"history": 1})
	history = session.get("history", []) if session else []
	recent_history = history[-5:]

	standalone_question = req.question
	if recent_history:
		standalone_question = query_rewrite.rewrite_query(recent_history, req.question)
	LOGGER.debug(
		"rewritten_question=%s session_id=%s history_length=%s",
		standalone_question,
		req.session_id,
		len(recent_history),
	)

	# 1) embed the question with BGE query prefix
	prefix = os.getenv("BGE_QUERY_PREFIX", "<|Query|> ")
	query_text = prefix + standalone_question
	try:
		q_embs = embed_module.embed_texts([query_text])
		if not q_embs:
			raise RuntimeError("embedding failed")
		q_vec = q_embs[0]
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"embedding error: {e}")

	user_id = req.user_id or os.getenv("DEFAULT_USER_ID", "local")
	min_fusion_score = float(os.getenv("MIN_FUSION_SCORE", "0.0"))
	answer_top_k = int(os.getenv("ANSWER_TOP_K", "5"))

	# 2) run vector and text search in parallel
	with ThreadPoolExecutor(max_workers=2) as executor:
		vector_future = executor.submit(
			retrieval.vector_search,
			q_vec,
			doc_id=req.doc_id,
			user_id=user_id,
			top_k=answer_top_k,
		)
		text_future = executor.submit(
			retrieval.text_search,
			standalone_question,
			doc_id=req.doc_id,
			user_id=user_id,
			top_k=15,
		)
	vector_results = vector_future.result()
	text_results = text_future.result()

	# 3) fuse candidate lists and apply threshold
	fused = retrieval.fuse_results(vector_results, text_results, w_vector=0.5, w_text=0.5)
	filtered = [entry for entry in fused if entry["fusion_score"] >= min_fusion_score]
	final_candidates = filtered[:answer_top_k]

	# 4) decide whether the retrieved context is sufficient
	if not final_candidates:
		answer_text = "I don't have enough information in this document to answer that."
		citations = []
		confidence = "low"
	else:
		answer_result = answer_module.generate_answer(
			standalone_question,
			[item["item"] for item in final_candidates],
			history=recent_history,
		)
		answer_text = answer_result.get("text", "I don't have enough information in this document to answer that.")
		citations = answer_result.get("citations", [])
		confidence = "high"

	# 5) save to session history
	sessions = mongo.db.get_collection("sessions")
	entry = {
		"question": req.question,
		"answer": answer_text,
		"timestamp": datetime.utcnow(),
		"candidates": [
			{
				"doc_id": item["item"].get("doc_id"),
				"item_id": item["item"].get("item_id"),
				"fusion_score": item["fusion_score"],
			}
			for item in final_candidates
		],
		"citations": citations,
	}
	sessions.update_one({"session_id": req.session_id}, {"$push": {"history": entry}}, upsert=True)

	LOGGER.debug(
		"ask=%s doc_id=%s user_id=%s vector_hits=%s text_hits=%s fused_hits=%s threshold_hits=%s",
		req.question,
		req.doc_id,
		user_id,
		len(vector_results),
		len(text_results),
		len(final_candidates),
		len(filtered),
	)

	return {"answer": answer_text, "citations": citations, "confidence": confidence}
