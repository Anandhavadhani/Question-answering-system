"""Embedding utilities.

Provides `embed_texts(texts: list[str]) -> list[list[float]]` which returns
embeddings for a list of texts using a BGE model wrapped by
`sentence-transformers`.

Note: Per project requirements we DO NOT apply BGE's instruction prefix
when embedding stored passages/captions. That prefix should only be
applied when embedding queries at retrieval time.
"""

from typing import List
import os

try:
	from sentence_transformers import SentenceTransformer
except Exception:
	SentenceTransformer = None


_MODEL = None


def _get_model():
	global _MODEL
	if _MODEL is not None:
		return _MODEL

	model_name = os.getenv("BGE_MODEL", os.getenv("BGE_MODEL_NAME", "BAAI/bge-base-en"))
	if SentenceTransformer is None:
		raise RuntimeError("sentence-transformers is not installed")
	try:
		_MODEL = SentenceTransformer(model_name)
	except Exception:
		# try a generic model name fallback
		try:
			_MODEL = SentenceTransformer("all-mpnet-base-v2")
		except Exception as e:
			raise RuntimeError(f"failed to load embedding model: {e}")
	return _MODEL


def embed_texts(texts: List[str]) -> List[List[float]]:
	"""Embed a list of texts and return list of float vectors.

	This function does NOT add any instruction prefix — embeddings produced
	here are intended for stored passages/captions.
	"""
	if not texts:
		return []
	model = _get_model()
	# SentenceTransformer returns numpy arrays; convert to native lists
	embeddings = model.encode(texts, show_progress_bar=False)
	# Ensure return is serializable list of lists
	try:
		return [list(map(float, v)) for v in embeddings]
	except Exception:
		# if embeddings is a single vector
		return [list(map(float, embeddings))]

