import os
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path('.').resolve()))

from app.db import mongo
from app.pipeline import embedding, retrieval
from app.routers.ask import router as ask_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def create_test_item(doc_id, item_id, text):
    embedding_vector = embedding.embed_texts([text])[0]
    doc = {
        'doc_id': doc_id,
        'item_id': item_id,
        'user_id': 'local',
        'type': 'native_text',
        'text': text,
        'embedding': embedding_vector,
        'metadata': {'page': 1, 'source_file': 'tmp_test.pdf', 'chunk_index': 0},
        'image_path': None,
    }
    mongo.collection.insert_one(doc)


def cleanup_doc(doc_id):
    mongo.collection.delete_many({'doc_id': doc_id})


def print_results(results, label):
    print(f'--- {label} ({len(results)} results) ---')
    for i, r in enumerate(results, 1):
        item = r.get('item', r)
        score = r.get('fusion_score', r.get('_score'))
        print(f'{i}. doc={item.get("doc_id")} item={item.get("item_id")} score={score} text={item.get("text")[:80]!r}')
    print()


def dump_breakdown(fused):
    print('--- fused breakdown ---')
    for row in fused:
        item = row['item']
        print(
            f"doc={item.get('doc_id')} item={item.get('item_id')} "
            f"vector={row['vector_score']:.6f} text={row['text_score']:.6f} "
            f"norm_vector={row['normalized_vector_score']:.6f} norm_text={row['normalized_text_score']:.6f} "
            f"fusion={row['fusion_score']:.6f} text={item.get('text')[:80]!r}"
        )
    print()


def main():
    print('collection count before:', mongo.collection.count_documents({}))

    base_sample = list(mongo.collection.find({}, {'doc_id': 1}).limit(10))
    distinct_doc_ids = mongo.collection.distinct('doc_id')
    print('distinct doc_ids:', distinct_doc_ids)
    if len(distinct_doc_ids) < 2:
        print('Need two distinct docs; inserting temporary docs')
        cleanup_doc('tmp-doc-1')
        cleanup_doc('tmp-doc-2')
        create_test_item('tmp-doc-1', str(uuid.uuid4()), 'Invoice 12345 total amount is $10,000. Reference ID 12345 in the table.')
        create_test_item('tmp-doc-2', str(uuid.uuid4()), 'This is unrelated document text without the invoice number.')
        distinct_doc_ids = ['tmp-doc-1', 'tmp-doc-2']
    print('running tests on doc_ids:', distinct_doc_ids[:2])

    query = 'Invoice 12345'
    q_emb = embedding.embed_texts([os.getenv('BGE_QUERY_PREFIX', '<|Query|> ') + query])[0]

    print('\nVector-only top results:')
    v_results = retrieval.vector_search(q_emb, doc_id=None, user_id='local', top_k=5)
    print_results(v_results, 'vector_search')

    print('Text-only top results:')
    t_results = retrieval.text_search(query, doc_id=None, user_id='local', top_k=5)
    print_results(t_results, 'text_search')

    fused = retrieval.fuse_results(v_results, t_results)
    dump_breakdown(fused)
    print('Fused top results:')
    print_results([{'item': r['item'], 'fusion_score': r['fusion_score']} for r in fused], 'fused')

    assert len(distinct_doc_ids) >= 2, 'Expected at least two doc_ids for filtering test'
    for doc_id in distinct_doc_ids[:2]:
        print(f'\nFiltering by doc_id={doc_id}')
        v_res = retrieval.vector_search(q_emb, doc_id=doc_id, user_id='local', top_k=5)
        t_res = retrieval.text_search(query, doc_id=doc_id, user_id='local', top_k=5)
        fused_res = retrieval.fuse_results(v_res, t_res)
        print_results(v_res, f'vector_search filtered {doc_id}')
        print_results(t_res, f'text_search filtered {doc_id}')
        print_results([{'item': r['item'], 'fusion_score': r['fusion_score']} for r in fused_res], f'fused filtered {doc_id}')

    # Use /ask router via TestClient to confirm the endpoint works with doc_id filtering
    app = FastAPI()
    app.include_router(ask_router, prefix='/ask', tags=['ask'])
    client = TestClient(app)
    print('\nTesting /ask endpoint for tmp-doc-1')
    response = client.post('/ask/', json={'session_id': 'tmp-session', 'doc_id': distinct_doc_ids[0], 'question': query, 'user_id': 'local'})
    print(response.status_code, response.json())

    print('\nTesting /ask endpoint for tmp-doc-2')
    response2 = client.post('/ask/', json={'session_id': 'tmp-session', 'doc_id': distinct_doc_ids[1], 'question': query, 'user_id': 'local'})
    print(response2.status_code, response2.json())

    print('cleanup temporary docs')
    if 'tmp-doc-1' in distinct_doc_ids or 'tmp-doc-2' in distinct_doc_ids:
        cleanup_doc('tmp-doc-1')
        cleanup_doc('tmp-doc-2')
    print('collection count after:', mongo.collection.count_documents({}))


if __name__ == '__main__':
    main()
