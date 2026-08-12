import os

# Make this top-level `app` package point to the real package under `backend/app`.
# This lets `uvicorn app.main:app` work when run from the repository root.
backend_app_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'app'))
if backend_app_path not in __path__:
    __path__.insert(0, backend_app_path)
