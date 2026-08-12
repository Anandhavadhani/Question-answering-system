from app.pipeline import retrieval

vector_results = [
    {"doc_id": "d1", "item_id": "i1", "_score": 10.0, "text": "A"},
    {"doc_id": "d1", "item_id": "i2", "_score": 5.0, "text": "B"},
]
text_results = [
    {"doc_id": "d1", "item_id": "i1", "_score": 2.0, "text": "A"},
    {"doc_id": "d1", "item_id": "i3", "_score": 8.0, "text": "C"},
]

fused = retrieval.fuse_results(vector_results, text_results)
for item in fused:
    print(item)
