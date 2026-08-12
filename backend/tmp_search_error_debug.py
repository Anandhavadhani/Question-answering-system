import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from app.db import mongo
from app.pipeline.retrieval import _build_filter_match

# Build both pipelines and run with explicit error capture
query = 'Invoice 12345'
vector_index = os.getenv('MONGO_VECTOR_INDEX_NAME', 'vector_index')
text_index = os.getenv('MONGO_TEXT_INDEX_NAME', 'bm25')

knn = {'vector': [0.0]*768, 'path': 'embedding', 'k': 1}
vector_pipeline = [
    {'$search': {'index': vector_index, 'knnBeta': knn}},
    {'$project': {'_id': 0, '_score': {'$meta': 'searchScore'}, 'doc_id': 1, 'item_id': 1, 'text': 1}},
    {'$limit': 1},
]

vect2_pipeline = [
    {'$search': {'index': vector_index, 'vectorSearch': {'queryVector': [0.0]*768, 'path': 'embedding', 'k': 1}}},
    {'$project': {'_id': 0, '_score': {'$meta': 'searchScore'}, 'doc_id': 1, 'item_id': 1, 'text': 1}},
    {'$limit': 1},
]
text_pipeline = [
    {'$search': {'index': text_index, 'text': {'query': query, 'path': 'text'}}},
    {'$project': {'_id': 0, '_score': {'$meta': 'searchScore'}, 'doc_id': 1, 'item_id': 1, 'text': 1}},
    {'$limit': 1},
]
for name, pipeline in [('knnBeta', vector_pipeline), ('vectorSearch', vect2_pipeline), ('text', text_pipeline)]:
    print('===', name, 'pipeline ===')
    print(pipeline)
    try:
        res = list(mongo.collection.aggregate(pipeline))
        print('RESULT', res)
    except Exception as e:
        print('ERROR', type(e).__name__, e)
    print()
