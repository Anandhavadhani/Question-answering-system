from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.pipeline import retrieval, embedding
from app.db import mongo

query = 'Native text on page 2'
print('query=', query)
q_emb = embedding.embed_texts([query])[0]
print('embedded len=', len(q_emb))
print('text_search result count:', len(retrieval.text_search(query, top_k=5)))
print('vector_search result count:', len(retrieval.vector_search(q_emb, top_k=5)))

# test doc_id filtering on existing doc_id
doc_ids = mongo.collection.distinct('doc_id')
print('doc_ids', doc_ids)
if doc_ids:
    doc_id = doc_ids[0]
    print('filtered text_search count', len(retrieval.text_search(query, doc_id=doc_id, top_k=5)))
    print('filtered vector_search count', len(retrieval.vector_search(q_emb, doc_id=doc_id, top_k=5)))
