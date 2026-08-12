"""Answer generation utilities.

This module provides an LLM-oriented prompt and a lightweight answer
implementation for the Groq vision model. It is intentionally simple for
Phase 5/6, but it already encodes the system prompt requirements for a
real LLM integration.
"""
from typing import List, Dict, Any, Optional

SYSTEM_PROMPT = (
	"You are a Groq vision assistant. Answer only from the provided retrieved "
	"text and images. Do not use any outside knowledge or infer facts that are "
	"not present in the provided context."
	"\n\nIf the retrieved context doesn't contain the answer, respond exactly:"
	"\nI don't have enough information in this document to answer that."
	"\n\nCite the page number and source item for every factual claim."
	"\nIf the retrieved passages conflict with each other, state that explicitly "
	"instead of silently picking one."
)


def _format_context(retrieved_items: List[Dict[str, Any]]) -> str:
	pieces = []
	for it in retrieved_items:
		t = it.get("text") or ""
		meta = it.get("metadata") or {}
		page = meta.get("page")
		item_id = it.get("item_id")
		source = meta.get("source_file")
		header_parts = []
		if page is not None:
			header_parts.append(f"page {page}")
		if item_id is not None:
			header_parts.append(f"item {item_id}")
		if source is not None:
			header_parts.append(f"source {source}")
		header = f"[{'; '.join(header_parts)}] " if header_parts else ""
		pieces.append(header + t)
	return "\n---\n".join(pieces)


def _extract_citations(answer_text: str, retrieved_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	citations = []
	seen = set()
	for it in retrieved_items:
		item_id = it.get("item_id")
		page = (it.get("metadata") or {}).get("page")
		source = (it.get("metadata") or {}).get("source_file")
		if item_id is None:
			continue
		pattern = f"item {item_id}"
		if pattern in answer_text:
			key = (item_id, page, source)
			if key not in seen:
				seen.add(key)
				citations.append({
					"item_id": item_id,
					"page": page,
					"source_file": source,
					"doc_id": it.get("doc_id"),
				})
	# fallback: if the answer did not reference explicit citation markers,
	# include the top retrieved sources conservatively.
	if not citations:
		for it in retrieved_items:
			item_id = it.get("item_id")
			if not item_id:
				continue
			key = (item_id, (it.get("metadata") or {}).get("page"), (it.get("metadata") or {}).get("source_file"))
			if key not in seen:
				seen.add(key)
				citations.append({
					"item_id": item_id,
					"page": (it.get("metadata") or {}).get("page"),
					"source_file": (it.get("metadata") or {}).get("source_file"),
					"doc_id": it.get("doc_id"),
				})
	return citations


def _truncate_text(text: str, max_chars: int = 550, max_lines: int = 5) -> str:
	cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
	if not cleaned_lines:
		return ''

	truncated_lines = cleaned_lines[:max_lines]
	truncated = '\n'.join(truncated_lines)
	if len(truncated) > max_chars:
		truncated = truncated[:max_chars].rstrip() + '...'
	elif len(cleaned_lines) > max_lines:
		truncated += '...'
	return truncated


def generate_answer(
	question: str,
	retrieved_items: List[Dict[str, Any]],
	history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
	"""Generate a structured answer with citations from the retrieved items."""
	if not retrieved_items:
		return {
			"text": "I don't have enough information in this document to answer that.",
			"citations": [],
		}

	best_item = retrieved_items[0]
	best_text = best_item.get('text', '').strip()
	answer_text = _truncate_text(best_text)
	if not answer_text:
		answer_text = "I don't have enough information in this document to answer that."

	citations = _extract_citations(answer_text, retrieved_items)
	if not citations:
		citations = [
			{
				"item_id": best_item.get('item_id'),
				"page": (best_item.get('metadata') or {}).get('page'),
				"source_file": (best_item.get('metadata') or {}).get('source_file'),
				"doc_id": best_item.get('doc_id'),
			}
		]

	return {"text": answer_text, "citations": citations}
