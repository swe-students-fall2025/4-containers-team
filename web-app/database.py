import pymongo
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from gridfs import GridFS
import os
from bson.objectid import ObjectId


# Build MongoDB connection URI from environment variables
# Fallback to MONGO_URI if provided, otherwise construct from components
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    mongodb_host = os.getenv("MONGODB_HOST", "localhost")
    mongodb_port = os.getenv("MONGODB_PORT", "27017")
    mongo_uri = f"mongodb://{mongodb_host}:{mongodb_port}/"

# Get database name from environment or use default
database_name = os.getenv("MONGODB_DATABASE", "proj4")

try:
    client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    # Test the connection
    db = client[database_name]
    
    # Initialize GridFS for file storage
    fs = GridFS(db)
    
    # Collection for metadata about uploads
    audio_uploads_collection = db["audio_uploads"]
    # Collection for analysis results
    analyses_collection = db["analyses"]
    print(f"Successfully connected to MongoDB database '{database_name}'")
    print(f"Using collection: 'audio_uploads'")
    print(f"Using collection: 'analyses'")
    print(f"GridFS will store files in: '{database_name}.fs.files' and '{database_name}.fs.chunks'")
except Exception as e:
    error_msg = f"Failed to connect to MongoDB at {mongo_uri}: {e}"
    print(f"ERROR: {error_msg}")
    raise ConnectionFailure(error_msg)
