from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.db import mongo
for doc_id in ['tmp-doc-1','tmp-doc-2']:
    print('DOC', doc_id, mongo.collection.count_documents({'doc_id': doc_id}))
    for d in mongo.collection.find({'doc_id': doc_id},{'item_id':1,'text':1}).limit(10):
        print(d)
