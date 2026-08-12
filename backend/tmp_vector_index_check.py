from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.db import mongo
from app.pipeline import embedding, retrieval

# pick an existing document with text and embedding
sample = mongo.collection.find_one({'text': {'$exists': True, '$ne': ''}})
print('sample doc:', sample and {'doc_id': sample.get('doc_id'), 'item_id': sample.get('item_id'), 'text': sample.get('text')[:80]})
if sample is None:
    raise SystemExit('no sample doc')

# use stored embedding if present, otherwise embed text
e = sample.get('embedding')
if not e:
    print('no embedding on sample; embedding text now')
    e = embedding.embed_texts([sample['text']])[0]
print('embedding len', len(e))

# run text search on the sample text
query = sample['text'][:40]
print('text_search query:', query)
text_res = retrieval.text_search(query, doc_id=sample['doc_id'], user_id='local', top_k=5)
print('text_search result count', len(text_res))
for r in text_res:
    print('text hit', r['doc_id'], r['item_id'], r['_score'], r['text'][:80])

# run vector search with the sample embedding
topk = 5
vec_res = retrieval.vector_search(e, doc_id=sample['doc_id'], user_id='local', top_k=topk)
print('vector_search result count', len(vec_res))
for r in vec_res:
    print('vector hit', r['doc_id'], r['item_id'], r['_score'], r['text'][:80])
