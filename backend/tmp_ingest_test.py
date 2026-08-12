from app.pipeline.ingestion import ingest_document
from app.db import mongo
from pathlib import Path

DOC_DIR = Path(__file__).resolve().parent / "data" / "uploads" / "9bd6cbb7-f04e-40fb-8970-ac3f509c8358"
PDF = DOC_DIR / "original.pdf"

print("Starting ingestion test for:", PDF)
try:
    res = ingest_document("39dedb84-0997-4dcb-887b-b75769a8fe88", str(PDF))
    print("Ingestion returned items:", len(res))
except Exception as e:
    print("Ingestion failed:", repr(e))

# Now query MongoDB for written items
try:
    coll = mongo.collection
    count = coll.count_documents({"doc_id": "39dedb84-0997-4dcb-887b-b75769a8fe88"})
    print(f"MongoDB documents for doc_id: {count}")
    # print a few sample docs
    cursor = coll.find({"doc_id": "39dedb84-0997-4dcb-887b-b75769a8fe88"}).limit(5)
    for d in cursor:
        emb = d.get("embedding")
        emb_len = len(emb) if emb else 0
        print({
            "item_id": d.get("item_id"),
            "type": d.get("type"),
            "text_len": len(d.get("text", "")),
            "embedding_len": emb_len,
            "metadata": d.get("metadata"),
        })
except Exception as e:
    print("MongoDB query failed:", repr(e))
