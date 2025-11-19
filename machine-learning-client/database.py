"""MongoDB helper utilities for the machine learning client."""

from __future__ import annotations

# Overall: get the MongoDB connection from env variables,
# build the document to store, and save the analysis result.
# Additionally, we provide a backup if we can't use DB for unit testing.
# Test 

# Allows for date and time operations
from datetime import datetime
import os
from typing import Any

# MongoDB driver imports
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, PyMongoError

# ---------------------------------------------------------------------------
# Connection configuration
# ---------------------------------------------------------------------------

# Looks for MongoDB connection URI from env var
MONGO_URI = os.getenv("MONGO_URI")
# If it doesn't exist, build it from components saved
if not MONGO_URI:
    host = os.getenv("MONGODB_HOST", "mongodb")
    port = os.getenv("MONGODB_PORT", "27017")
    username = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")

    credentials = ""
    if username and password:
        credentials = f"{username}:{password}@"
    MONGO_URI = f"mongodb://{credentials}{host}:{port}/"

# Picks the database name, defaulting to "ml_data"
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "ml_data")
ANALYSES_COLLECTION = os.getenv("MONGODB_ANALYSES_COLLECTION", "analyses")

_client: MongoClient | None = None
_collection: Collection | None = None
_db_available = False

# Fallback store used in tests or when MongoDB is offline.
_in_memory_store: list[dict[str, Any]] = []


# Initializes the connection to MongoDB
def _init_connection() -> None:
    """Lazily connect to MongoDB."""
    global _client, _collection, _db_available  # pylint: disable=global-statement

    if _client is not None:
        return

    try:
        candidate = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        candidate.admin.command("ping")
        _client = candidate
        _collection = _client[DATABASE_NAME][ANALYSES_COLLECTION]
        _db_available = True
        print(
            f"[INFO] ML client connected to MongoDB at {MONGO_URI}, "
            f"db '{DATABASE_NAME}', collection '{ANALYSES_COLLECTION}'"
        )
    except ConnectionFailure as exc:
        print(f"[WARNING] ML client could not connect to MongoDB ({MONGO_URI}): {exc}")
        _client = None
        _collection = None
        _db_available = False


# Packages the document to store it into MongoDB
def _build_document(
    *,
    audio_path: str,  # path to the audio file
    language: str,  # detected language
    transcript: str | None,  # transcribed text
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the document stored in MongoDB."""
    document: dict[str, Any] = {
        "audio_path": audio_path,
        "language": language,
        "transcript": transcript,
        "analysis_date": datetime.utcnow(),
    }
    if extra_fields:
        document.update(extra_fields)
    return document


# This is the primary function to save analysis results into DB
# Accepts both lang and language kwargs for compatibility
def save_result(
    *,
    audio_path: str,
    lang: str | None = None,
    language: str | None = None,
    transcript: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> Any:
    # decides on the detected language or falls back to "unknown"
    detected_language = language or lang or "unknown"
    document = _build_document(
        audio_path=audio_path,
        language=detected_language,
        transcript=transcript,
        extra_fields=extra_fields,
    )

    _init_connection()

    # Attempt to store in MongoDB if available
    if _db_available and _collection is not None:
        try:
            result = _collection.insert_one(document)
            return result.inserted_id
        except PyMongoError as exc:
            print(f"[WARNING] Failed to write ML analysis to MongoDB: {exc}")

    # This is a fallback to in-memory storage if DB isn't working
    document["_id"] = f"in-memory-{len(_in_memory_store) + 1}"
    _in_memory_store.append(document)
    return document["_id"]


# Retrieves all cached results from in-memory store
def get_cached_results() -> list[dict[str, Any]]:
    return list(_in_memory_store)
