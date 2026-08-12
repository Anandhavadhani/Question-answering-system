from app.db import mongo

coll = mongo.collection
print('collection:', mongo.MONGO_COLLECTION, 'db:', mongo.MONGO_DB)
print('total docs:', coll.count_documents({}))
print('distinct doc_ids:', coll.distinct('doc_id')[:20])
print('sample docs:')
for d in coll.find({}, {'doc_id': 1, 'item_id': 1, 'text': 1}).limit(10):
    print(d)
