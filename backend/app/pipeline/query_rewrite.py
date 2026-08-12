"""Query rewriting utilities."""

import os
from typing import List, Dict, Any

REWRITE_SYSTEM_PROMPT = (
	"You are a lightweight text-only Groq assistant. Rewrite the user's new "
	"question into a standalone question that does not depend on prior "
	"conversation history. Do not answer the question."
)


def _format_history(history: List[Dict[str, Any]]) -> str:
	pieces = []
	for turn in history:
		q = turn.get("question", "")
		a = turn.get("answer", "")
		pieces.append(f"Q: {q}\nA: {a}")
	return "\n\n".join(pieces)


def _build_rewrite_prompt(history: List[Dict[str, Any]], new_question: str) -> str:
	history_text = _format_history(history)
	return (
		f"{REWRITE_SYSTEM_PROMPT}\n\n"
		f"Conversation history:\n{history_text}\n\n"
		f"New question: {new_question}\n\n"
		"Rewrite the new question as a standalone question that contains all "
		"relevant context from the prior turns and can be answered on its own."
	)


def _extract_text_output(response_json: Dict[str, Any]) -> str:
	if not isinstance(response_json, dict):
		return ""
	for key in ("output", "result", "text", "response", "choices"):
		value = response_json.get(key)
		if isinstance(value, str):
			return value.strip()
		if isinstance(value, list) and value:
			first = value[0]
			if isinstance(first, dict):
				text_val = first.get("text") or first.get("content")
				if isinstance(text_val, str):
					return text_val.strip()
			if isinstance(first, str):
				return first.strip()
	return ""


def _call_groq_text_model(prompt: str) -> str:
	api_key = os.getenv("GROQ_API_KEY")
	model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.1-8b-instant")
	endpoint = os.getenv("GROQ_TEXT_API_URL", "https://api.groq.com/v1/text")
	if not api_key:
		raise RuntimeError("GROQ_API_KEY is required for query rewriting")
	try:
		import requests
	except ImportError:
		raise RuntimeError("requests is required for Groq text rewrite calls")

	response = requests.post(
		endpoint,
		headers={
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
		},
		json={"model": model_name, "input": prompt},
		timeout=30,
	)
	response.raise_for_status()
	return _extract_text_output(response.json())


def rewrite_query(history: List[Dict[str, Any]], new_question: str) -> str:
	"""Rewrite a follow-up question into a standalone question."""
	if not history:
		return new_question

	history = history[-5:]
	prompt = _build_rewrite_prompt(history, new_question)
	try:
		return _call_groq_text_model(prompt) or new_question
	except Exception:
		# If the external rewrite call is unavailable, keep the original question.
		return new_question
