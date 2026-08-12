from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.db import mongo

try:
    print('db command result:', mongo.db.command({'listSearchIndexes': mongo.collection.name}))
except Exception as e:
    print('listSearchIndexes error:', type(e).__name__, e)
