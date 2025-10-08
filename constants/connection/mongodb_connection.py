from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

class mongo_connection:
    mongo_client = MongoClient(os.getenv("MONGODB_URL"))
    db = mongo_client["news_db"]
    collection = db["aspects"]