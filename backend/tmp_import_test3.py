import sys
try:
    import logging
    from app.routers import ask
    from app.pipeline import retrieval
    print('imports OK')
except Exception as e:
    print('import error', repr(e))
    sys.exit(1)
