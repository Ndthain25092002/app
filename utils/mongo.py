from bson import ObjectId

def fix_mongo_ids(data):
    if isinstance(data, list):
        return [fix_mongo_ids(x) for x in data]
    if isinstance(data, dict):
        return {k: fix_mongo_ids(v) for k, v in data.items()}
    if isinstance(data, ObjectId):
        return str(data)
    return data
