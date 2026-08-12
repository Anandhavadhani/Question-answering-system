import sys
try:
    from app.routers import ask, sessions
    from app.pipeline import retrieval, answer, embedding
    print('imports OK')
except Exception as e:
    print('import error', repr(e))
    sys.exit(1)
