import os
from pathlib import Path
from typing import List, Dict, Any

from pymongo import MongoClient, ReplaceOne
from dotenv import load_dotenv

# Load the backend/.env file explicitly so the Mongo config works regardless of cwd.
backend_env = Path(__file__).resolve().parents[2] / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
else:
    load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", os.getenv("MONGO_DB_NAME", "rag"))
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", os.getenv("MONGO_COLLECTION_NAME", "documents"))

# Create a global client/collection reference for simple use in the pipeline.
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]


def save_items(doc_id: str, items: List[Dict[str, Any]]) -> None:
	"""Save a list of items to MongoDB using the required schema.

	Each item in `items` is expected to contain at least the following
	keys (some may be optional depending on type):
	  - item_id: str
	  - type: 'native_text'|'ocr_text'|'caption'
	  - text: str
	  - embedding: list[float]
	  - metadata: dict (must include 'page', 'source_file', 'chunk_index')
	  - image_path: str or None

	The function writes/overwrites documents in the collection keyed by
	(doc_id, item_id). The `user_id` field is hardcoded to "local".
	"""
	if not items:
		return

	ops = []
	for it in items:
		item_id = it.get("item_id") or it.get("id")
		if not item_id:
			# Skip items without an id
			continue

		doc = {
			"doc_id": doc_id,
			"item_id": item_id,
			"user_id": "local",
			"type": it.get("type"),
			"text": it.get("text"),
			"embedding": it.get("embedding"),
			"metadata": it.get("metadata", {}),
			"image_path": it.get("image_path", None),
		}

		# Use a ReplaceOne upsert to overwrite existing item_id for same doc
		ops.append(
			ReplaceOne({"doc_id": doc_id, "item_id": item_id}, doc, upsert=True)
		)

	if not ops:
		return

	# Bulk write for efficiency
	collection.bulk_write(ops)

