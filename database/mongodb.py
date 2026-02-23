import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "crm_database")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]

def get_collection(name: str):
    return db[name]

def get_db():
    return db
