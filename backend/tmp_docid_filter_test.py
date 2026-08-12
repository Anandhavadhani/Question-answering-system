from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path('.').resolve()))
from app.db import mongo
from app.pipeline import embedding, retrieval, answer
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.ask import router as ask_router


def create_doc(doc_id, item_id, text):
    vec = embedding.embed_texts([text])[0]
    doc = {
        'doc_id': doc_id,
        'item_id': item_id,
        'user_id': 'local',
        'type': 'native_text',
        'text': text,
        'embedding': vec,
        'metadata': {'page': 2, 'source_file': 'tmp_test.pdf', 'chunk_index': 0},
        'image_path': None,
    }
    mongo.collection.insert_one(doc)


def cleanup(doc_id):
    mongo.collection.delete_many({'doc_id': doc_id})


def print_res(results, label):
    print('---', label, '---')
    for i, r in enumerate(results, 1):
        item = r.get('item', r)
        print(f'{i}. doc={item.get("doc_id")} item={item.get("item_id")} score={r.get("fusion_score", r.get("_score"))} text={item.get("text")!r}')
    print()


def main():
    doc1 = 'tmp-doc-filter-1'
    doc2 = 'tmp-doc-filter-2'
    cleanup(doc1)
    cleanup(doc2)
    create_doc(doc1, str(uuid.uuid4()), 'Invoice 12345 total due is $10,000 on page 2. Reference ID 12345.')
    create_doc(doc2, str(uuid.uuid4()), 'Different document content. This has no invoice number, but it does mention page 2 otherwise.')

    query = 'Invoice 12345'
    q_prefix = '<|Query|> '
    q_emb = embedding.embed_texts([q_prefix + query])[0]

    v_results = retrieval.vector_search(q_emb, doc_id=None, user_id='local', top_k=5)
    t_results = retrieval.text_search(query, doc_id=None, user_id='local', top_k=5)
    fused = retrieval.fuse_results(v_results, t_results)

    print('QUERY:', query)
    print('vector_search count:', len(v_results))
    print('text_search count:', len(t_results))
    print_res(v_results, 'vector_search')
    print_res(t_results, 'text_search')
    print_res(fused, 'fused')
    print('FUSED breakdown:')
    for row in fused:
        item = row['item']
        print(f"doc={item['doc_id']} item={item['item_id']} vector={row['vector_score']} text={row['text_score']} norm_vector={row['normalized_vector_score']:.3f} norm_text={row['normalized_text_score']:.3f} fusion={row['fusion_score']:.3f}")
    print()

    print('Filter doc_id=', doc1)
    t1 = retrieval.text_search(query, doc_id=doc1, user_id='local', top_k=5)
    v1 = retrieval.vector_search(q_emb, doc_id=doc1, user_id='local', top_k=5)
    print('text_search filtered count:', len(t1), 'vector_search filtered count:', len(v1))
    print_res(t1, f'text_search filtered {doc1}')
    print_res(v1, f'vector_search filtered {doc1}')

    print('Filter doc_id=', doc2)
    t2 = retrieval.text_search(query, doc_id=doc2, user_id='local', top_k=5)
    v2 = retrieval.vector_search(q_emb, doc_id=doc2, user_id='local', top_k=5)
    print('text_search filtered count:', len(t2), 'vector_search filtered count:', len(v2))
    print_res(t2, f'text_search filtered {doc2}')
    print_res(v2, f'vector_search filtered {doc2}')

    app = FastAPI()
    app.include_router(ask_router, prefix='/ask', tags=['ask'])
    client = TestClient(app)
    response = client.post('/ask/', json={'session_id': 'tmp-session', 'doc_id': doc1, 'question': query, 'user_id': 'local'})
    print('/ask doc1', response.status_code, response.json())
    response = client.post('/ask/', json={'session_id': 'tmp-session', 'doc_id': doc2, 'question': query, 'user_id': 'local'})
    print('/ask doc2', response.status_code, response.json())

    cleanup(doc1)
    cleanup(doc2)

if __name__ == '__main__':
    main()
