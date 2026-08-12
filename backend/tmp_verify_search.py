from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
import os

load_dotenv(Path(__file__).resolve().parent / '.env')
uri = os.getenv('MONGO_URI')
db_name = os.getenv('MONGO_DB', os.getenv('MONGO_DB_NAME', 'rag'))
coll_name = os.getenv('MONGO_COLLECTION', os.getenv('MONGO_COLLECTION_NAME', 'documents'))
text_index_name = os.getenv('MONGO_TEXT_INDEX_NAME', 'default')
vector_index_name = os.getenv('MONGO_VECTOR_INDEX_NAME', 'default')

client = MongoClient(uri)
db = client[db_name]
coll = db[coll_name]

print('uri', uri)
print('db', db_name)
print('collection', coll_name)
print('text_index_name', text_index_name)
print('vector_index_name', vector_index_name)
print('count', coll.count_documents({}))

try:
    print('listSearchIndexes command result:')
    result = db.command({'listSearchIndexes': coll_name})
    print(result)
except Exception as err:
    print('listSearchIndexes error:', type(err).__name__, err)

sample_doc = coll.find_one({}, {'text': 1})
sample_text = sample_doc.get('text', '') if sample_doc else ''
print('sample text start:', sample_text[:200].replace('\n', ' '))

query_term = None
if sample_text:
    tokens = [token.strip('.,;:!?()[]"\'') for token in sample_text.split() if len(token.strip('.,;:!?()[]"\'')) > 3]
    query_term = tokens[0] if tokens else None

if query_term:
    print('using search query term:', query_term)
    try:
        result = list(coll.aggregate([
            {'$search': {'index': text_index_name, 'text': {'query': query_term, 'path': 'text'}}},
            {'$limit': 3}
        ]))
        print('text search result count:', len(result))
        print(result)
    except Exception as err:
        print('$search error:', type(err).__name__, err)
else:
    print('no query term available from sample text')

try:
    print('aggregate $search with knnBeta operator result:')
    result = list(coll.aggregate([
        {'$search': {'index': vector_index_name, 'knnBeta': {'path': 'embedding', 'vector': [0.0] * 768, 'k': 1}}},
        {'$limit': 1}
    ]))
    print('knnBeta result count:', len(result))
    print(result)
except Exception as err:
    print('$search knnBeta error:', type(err).__name__, err)

try:
    print('aggregate $search with vectorSearch operator using existing embedding:')
    sample_embedding_doc = coll.find_one({'embedding': {'$exists': True}}, {'embedding': 1})
    sample_vector = sample_embedding_doc['embedding'] if sample_embedding_doc else None
    if sample_vector:
        result = list(coll.aggregate([
            {'$search': {'index': vector_index_name, 'vectorSearch': {'path': 'embedding', 'queryVector': sample_vector, 'limit': 1, 'numCandidates': 10}}},
            {'$limit': 1}
        ]))
        print('vectorSearch result count:', len(result))
        print(result)
    else:
        print('no sample embedding available for vector search')
except Exception as err:
    print('$search vector error:', type(err).__name__, err)
