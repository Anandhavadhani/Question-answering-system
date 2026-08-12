"""Retrieval utilities.

Provides Atlas search helpers for vector, text, and fused ranking.
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
import os

from app.db import mongo

LOGGER = logging.getLogger(__name__)


def _run_pipeline(pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	return list(mongo.collection.aggregate(pipeline))


def _cosine_similarity(a: List[float], b: List[float]) -> float:
	if not a or not b or len(a) != len(b):
		return 0.0
	adotb = sum(x * y for x, y in zip(a, b))
	anorm = (sum(x * x for x in a)) ** 0.5
	bnorm = (sum(y * y for y in b)) ** 0.5
	if anorm == 0 or bnorm == 0:
		return 0.0
	return adotb / (anorm * bnorm)


def _apply_vector_scores(results: List[Dict[str, Any]], query_embedding: List[float]) -> List[Dict[str, Any]]:
	for result in results:
		if result.get("_score") is None:
			embedding = result.get("embedding")
			result["_score"] = _cosine_similarity(query_embedding, embedding or [])
	return results


def _filter_results_by_scope(results: List[Dict[str, Any]], doc_id: Optional[str], user_id: Optional[str]) -> List[Dict[str, Any]]:
	if not results:
		return []
	if not doc_id and not user_id:
		return results
	filtered = []
	for item in results:
		if doc_id and item.get("doc_id") != doc_id:
			continue
		if user_id and item.get("user_id") != user_id:
			continue
		filtered.append(item)
	return filtered


def _safe_run_pipeline(pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	try:
		return _run_pipeline(pipeline)
	except Exception as e:
		LOGGER.debug("search pipeline failed: %s pipeline=%s", e, pipeline)
		return []


def _build_vector_search_pipelines(query_embedding: List[float], vector_index: str, top_k: int) -> List[Dict[str, Any]]:
	"""Generate fallback vector search pipelines for different Atlas operator variants."""
	return [
		{"$search": {"index": vector_index, "knnBeta": {"vector": query_embedding, "path": "embedding", "k": int(top_k)}}},
		{"$search": {"index": vector_index, "knnBeta": {"queryVector": query_embedding, "path": "embedding", "k": int(top_k)}}},
		{"$vectorSearch": {"index": vector_index, "queryVector": query_embedding, "path": "embedding", "limit": int(top_k), "numCandidates": max(int(top_k) * 5, 50)}},
		{"$vectorSearch": {"index": vector_index, "vector": query_embedding, "path": "embedding", "limit": int(top_k), "numCandidates": max(int(top_k) * 5, 50)}},
	]


def vector_search(query_embedding: List[float], doc_id: Optional[str] = None, user_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
	"""Run a MongoDB Atlas vector search against the `embedding` field."""
	vector_index = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")

	for variant, search_stage in zip(
		["knnBeta(vector)", "knnBeta(queryVector)", "$vectorSearch(queryVector)", "$vectorSearch(vector)"],
		_build_vector_search_pipelines(query_embedding, vector_index, top_k),
	):
		pipeline: List[Dict[str, Any]] = [
			search_stage,
			{"$project": {"_id": 0, "_score": {"$meta": "searchScore"}, "doc_id": 1, "item_id": 1, "type": 1, "text": 1, "embedding": 1, "metadata": 1, "image_path": 1, "user_id": 1}},
			{"$limit": int(top_k)},
		]

		try:
			results = _run_pipeline(pipeline)
			results = _filter_results_by_scope(results, doc_id, user_id)
			results = _apply_vector_scores(results, query_embedding)
			if results:
				LOGGER.debug("vector_search using %s returned %d results", variant, len(results))
				return results
			LOGGER.debug("vector_search using %s returned no results", variant)
		except Exception as e:
			LOGGER.debug("vector_search %s failed: %s", variant, e)

	LOGGER.debug("vector_search: all vector search variants failed or returned no hits")
	return []


def text_search(query: str, doc_id: Optional[str] = None, user_id: Optional[str] = None, top_k: int = 15) -> List[Dict[str, Any]]:
	"""Run a MongoDB Atlas text search against the `text` field."""
	text_index = os.getenv("MONGO_TEXT_INDEX_NAME", "bm25")
	search_stage: Dict[str, Any] = {
		"$search": {
			"index": text_index,
			"text": {"query": query, "path": "text"},
		}
	}

	pipeline: List[Dict[str, Any]] = [search_stage]

	pipeline.extend([
		{"$project": {"_id": 0, "_score": {"$meta": "searchScore"}, "doc_id": 1, "item_id": 1, "type": 1, "text": 1, "embedding": 1, "metadata": 1, "image_path": 1, "user_id": 1}},
		{"$limit": int(top_k)},
	])
	results = _run_pipeline(pipeline)
	return _filter_results_by_scope(results, doc_id, user_id)


def normalize_scores(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	"""Min-max normalize a list of {'item': item, 'score': score} dictionaries."""
	if not results:
		return []

	scores = [float(r.get("score", 0.0)) for r in results]
	min_score = min(scores)
	max_score = max(scores)
	if max_score == min_score:
		return [{**r, "normalized_score": 1.0} for r in results]

	return [
		{
			**r,
			"normalized_score": (float(r.get("score", 0.0)) - min_score) / (max_score - min_score),
		}
		for r in results
	]


def _item_key(item: Dict[str, Any]) -> Tuple[str, str]:
	return (item.get("doc_id", ""), item.get("item_id", ""))


def fuse_results(
	vector_results: List[Dict[str, Any]],
	text_results: List[Dict[str, Any]],
	w_vector: float = 0.5,
	w_text: float = 0.5,
) -> List[Dict[str, Any]]:
	"""Fuse vector and text result sets using normalized scores."""
	vector_input = [{"item": r, "score": float(r.get("_score", 0.0))} for r in vector_results]
	text_input = [{"item": r, "score": float(r.get("_score", 0.0))} for r in text_results]

	vector_norm = normalize_scores(vector_input)
	text_norm = normalize_scores(text_input)

	indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}

	for entry in vector_norm:
		key = _item_key(entry["item"])
		indexed.setdefault(key, {
			"item": entry["item"],
			"vector_score": entry["score"],
			"normalized_vector_score": entry["normalized_score"],
			"text_score": 0.0,
			"normalized_text_score": 0.0,
		})

	for entry in text_norm:
		key = _item_key(entry["item"])
		record = indexed.setdefault(key, {
			"item": entry["item"],
			"vector_score": 0.0,
			"normalized_vector_score": 0.0,
			"text_score": 0.0,
			"normalized_text_score": 0.0,
		})
		record["text_score"] = entry["score"]
		record["normalized_text_score"] = entry["normalized_score"]

	fused: List[Dict[str, Any]] = []
	for record in indexed.values():
		fusion_score = w_vector * record["normalized_vector_score"] + w_text * record["normalized_text_score"]
		entry = {
			"item": record["item"],
			"vector_score": record["vector_score"],
			"text_score": record["text_score"],
			"normalized_vector_score": record["normalized_vector_score"],
			"normalized_text_score": record["normalized_text_score"],
			"fusion_score": fusion_score,
		}
		fused.append(entry)

	fused.sort(key=lambda x: x["fusion_score"], reverse=True)

	for r in fused:
		LOGGER.debug(
			"candidate %s/%s raw vector=%.6f raw text=%.6f norm vector=%.6f norm text=%.6f fusion=%.6f",
			r["item"].get("doc_id", ""),
			r["item"].get("item_id", ""),
			r["vector_score"],
			r["text_score"],
			r["normalized_vector_score"],
			r["normalized_text_score"],
			r["fusion_score"],
		)

	return fused
