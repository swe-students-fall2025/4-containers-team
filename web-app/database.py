import pymongo
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId


mongo_uri = os.getenv("MONGO_URI")
client = pymongo.MongoClient(mongo_uri)
db = client["proj4"]
audio_uploads_collection = db["audio_uploads"]
