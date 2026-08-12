from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.db import mongo
from app.pipeline import embedding

# sample embedding
sample = mongo.collection.find_one({'embedding': {'$exists': True}}, {'embedding': 1, 'text': 1, 'doc_id': 1, 'item_id': 1})
if not sample:
    raise SystemExit('No sample document with embedding')
print('sample doc_id', sample.get('doc_id'), 'item_id', sample.get('item_id'))
query_vector = sample['embedding']
print('vector len', len(query_vector))

pipelines = [
    [{'$vectorSearch': {'index': 'vector_index', 'queryVector': query_vector, 'path': 'embedding', 'k': 3, 'numCandidates': 20}}],
    [{'$vectorSearch': {'index': 'vector_index', 'vector': query_vector, 'path': 'embedding', 'k': 3, 'numCandidates': 20}}],
    [{'$search': {'index': 'vector_index', 'vectorSearch': {'queryVector': query_vector, 'path': 'embedding', 'k': 3, 'numCandidates': 20}}}],
    [{'$search': {'index': 'vector_index', 'vectorSearch': {'vector': query_vector, 'path': 'embedding', 'k': 3, 'numCandidates': 20}}}],
]

for idx, p in enumerate(pipelines, 1):
    print('--- pipeline', idx, p)
    try:
        result = list(mongo.collection.aggregate(p))
        print('count', len(result))
        print(result[:2])
    except Exception as err:
        print('error', type(err).__name__, err)

# Also test text stage for same query
try:
    print('--- text search with "Native"')
    result = list(mongo.collection.aggregate([
        {'$search': {'index': 'bm25', 'text': {'query': 'Native', 'path': 'text'}}},
        {'$limit': 3}
    ]))
    print('text search count', len(result))
except Exception as err:
    print('text search error', type(err).__name__, err)
