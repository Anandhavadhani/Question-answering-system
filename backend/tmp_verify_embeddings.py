from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
import os

load_dotenv(Path(__file__).resolve().parent / '.env')
uri = os.getenv('MONGO_URI')
db_name = os.getenv('MONGO_DB', os.getenv('MONGO_DB_NAME', 'rag'))
coll_name = os.getenv('MONGO_COLLECTION', os.getenv('MONGO_COLLECTION_NAME', 'documents'))

client = MongoClient(uri)
db = client[db_name]
coll = db[coll_name]

print('uri', uri)
print('db', db_name)
print('collection', coll_name)
print('count', coll.count_documents({}))

for i, doc in enumerate(coll.find({}, {'item_id': 1, 'type': 1, 'embedding': 1}).limit(10)):
    emb = doc.get('embedding')
    print('doc', i, 'item_id', doc.get('item_id'), 'type', doc.get('type'), 'emb_type', type(emb).__name__, 'emb_exists', 'embedding' in doc, 'emb_len', len(emb) if isinstance(emb, list) else emb)
