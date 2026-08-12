import logging
from app.routers import ask as ask_module
from app.pipeline import answer as answer_module
from app.routers.ask import AskRequest
from app.pipeline import embedding as embed_module
from app.pipeline import retrieval
orig_embed = embed_module.embed_texts
orig_vector = retrieval.vector_search
orig_text = retrieval.text_search
orig_fuse = retrieval.fuse_results
orig_generate = answer_module.generate_answer
logger = logging.getLogger('app.routers.ask')
logger.setLevel(logging.DEBUG)
stream = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
stream.setFormatter(formatter)
logger.addHandler(stream)
print('--- RUNNING ABSTAIN CHECK ---')
embed_module.embed_texts = lambda texts: [[0.0] * 768]
retrieval.vector_search = lambda *args, **kwargs: []
retrieval.text_search = lambda *args, **kwargs: []
retrieval.fuse_results = lambda v, t, **kwargs: []
def fail_generate_answer(question, retrieved_items):
    raise RuntimeError('generate_answer should not be called for abstain case')
answer_module.generate_answer = fail_generate_answer
req = AskRequest(session_id='test-session', question='Who won the 2024 World Cup?', doc_id='doc-1')
result = ask_module.ask(req)
print('UNANSWERABLE RESULT:', result)
embed_module.embed_texts = orig_embed
retrieval.vector_search = orig_vector
retrieval.text_search = orig_text
retrieval.fuse_results = orig_fuse
answer_module.generate_answer = orig_generate
print('--- RUNNING IN-DOCUMENT CITATION CHECK ---')
embed_module.embed_texts = lambda texts: [[0.0] * 768]
retrieval.vector_search = lambda *args, **kwargs: []
retrieval.text_search = lambda *args, **kwargs: []
def fuse_results(v, t, **kwargs):
    return [
        {
            'fusion_score': 1.0,
            'item': {
                'item_id': 'item-123',
                'doc_id': 'doc-1',
                'text': 'This document states that the capital is Paris.',
                'metadata': {'page': 5, 'source_file': 'sample3.pdf'},
            },
        }
    ]
retrieval.fuse_results = fuse_results
req2 = AskRequest(session_id='test-session', question='What is the capital mentioned in this document?', doc_id='doc-1')
result2 = ask_module.ask(req2)
print('IN-DOCUMENT RESULT:', result2)
embed_module.embed_texts = orig_embed
retrieval.vector_search = orig_vector
retrieval.text_search = orig_text
retrieval.fuse_results = orig_fuse
answer_module.generate_answer = orig_generate
