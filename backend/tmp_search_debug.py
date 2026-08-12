from app.db import mongo

coll = mongo.collection

for search_spec in [
    {"$search": {"index": "bm25", "text": {"query": "Invoice 12345", "path": "text"}}},
    {"$search": {"index": "vector_index", "knnBeta": {"vector": [0.0]*768, "path": "embedding", "k": 1}}},
]:
    pipeline = [search_spec, {"$limit": 1}]
    try:
        print('Trying', search_spec)
        res = list(coll.aggregate(pipeline))
        print('OK', res)
    except Exception as exc:
        print('ERROR', type(exc).__name__, exc)
