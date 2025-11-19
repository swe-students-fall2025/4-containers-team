"""MongoDB helpers for the machine-learning client."""

# Overall: get the MongoDB connection from env variables,
# build the document to store, and save the analysis result.
# Additionally, we provide a backup if we can't use DB for unit testing.
# Test upload

# Allows for date and time operations
from datetime import datetime
import os
from typing import Any, Optional
import traceback

# MongoDB driver imports
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, PyMongoError
from gridfs import GridFS
from bson import ObjectId

# ---------------------------------------------------------------------------
# Connection configuration
# ---------------------------------------------------------------------------


def _default_mongo_uri() -> str:
    """Build the Mongo URI from discrete environment variables."""
    host = os.getenv("MONGODB_HOST", "mongodb")
    port = os.getenv("MONGODB_PORT", "27017")
    username = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")

    credentials_fragment = ""
    if username and password:
        credentials_fragment = f"{username}:{password}@"
    return f"mongodb://{credentials_fragment}{host}:{port}/"


# Looks for MongoDB connection URI from env var
MONGO_URI = os.getenv("MONGO_URI") or _default_mongo_uri()

# Picks the database name, defaulting to "proj4"
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "proj4")
ANALYSES_COLLECTION = os.getenv("MONGODB_ANALYSES_COLLECTION", "analyses")

_client: Optional[MongoClient] = None
_db: Optional[Any] = None
_collection: Optional[Collection] = None
_fs: Optional[GridFS] = None
_audio_uploads_collection: Optional[Collection] = None
_db_available = False  # pylint: disable=invalid-name

# Fallback store used in tests or when MongoDB is offline.
_in_memory_store: list[dict[str, Any]] = []


# Initializes the connection to MongoDB
def _init_connection() -> None:
    """Lazily connect to MongoDB."""
    global _client, _db, _collection, _fs, _audio_uploads_collection, _db_available  # pylint: disable=global-statement

    if _client is not None:
        return

    try:
        candidate = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        candidate.admin.command("ping")
        _client = candidate
        _db = _client[DATABASE_NAME]
        _collection = _db[ANALYSES_COLLECTION]
        _fs = GridFS(_db)
        _audio_uploads_collection = _db["audio_uploads"]
        _db_available = True
        print(
            f"[INFO] ML client connected to MongoDB at {MONGO_URI}, "
            f"db '{DATABASE_NAME}', collection '{ANALYSES_COLLECTION}'"
        )
    except ConnectionFailure as exc:
        print(f"[WARNING] ML client could not connect to MongoDB ({MONGO_URI}): {exc}")
        _client = None
        _db = None
        _collection = None
        _fs = None
        _audio_uploads_collection = None
        _db_available = False


# Packages the document to store it into MongoDB
def _build_document(
    *,
    audio_path: str,  # path to the audio file
    language: str,  # detected language
    transcript: Optional[str],  # transcribed text
    extra_fields: Optional[dict[str, Any]] = None,
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
    lang: Optional[str] = None,
    language: Optional[str] = None,
    transcript: Optional[str] = None,
    extra_fields: Optional[dict[str, Any]] = None,
) -> Any:
    """Persist an analysis document to MongoDB or the in-memory fallback."""
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
            inserted_id = result.inserted_id
            print(
                f"[INFO] Successfully saved analysis to MongoDB with ID: {inserted_id}"
            )

            # Verify the document was actually saved
            verify_doc = _collection.find_one({"_id": inserted_id})
            if verify_doc:
                print("[INFO] Verified: Document exists in database")
            else:
                print("[WARNING] Verification failed: Document not found after insert!")

            return inserted_id
        except PyMongoError as exc:
            print(f"[ERROR] Failed to store analysis in MongoDB: {exc}")
            traceback.print_exc()
    else:
        warning_msg = (
            "[WARNING] Database not available. "
            f"_db_available={_db_available}, _collection={_collection}"
        )
        print(warning_msg)
        if _collection is None:
            collection_warning = (
                "[WARNING] Collection is None. "
                f"DATABASE_NAME='{DATABASE_NAME}', "
                f"ANALYSES_COLLECTION='{ANALYSES_COLLECTION}'"
            )
            print(collection_warning)

    # This is a fallback to in-memory storage if DB isn't working
    print("[WARNING] Falling back to in-memory storage (data will be lost on restart)")
    document["_id"] = f"in-memory-{len(_in_memory_store) + 1}"
    _in_memory_store.append(document)
    return document["_id"]


# Retrieves all cached results from in-memory store
def get_cached_results() -> list[dict[str, Any]]:
    """Return a shallow copy of the in-memory analysis cache."""
    return list(_in_memory_store)


def get_all_results() -> list[dict[str, Any]]:
    """Fetch all analysis results from MongoDB, or from in-memory fallback."""
    _init_connection()

    # If MongoDB is available
    if _db_available and _collection is not None:
        try:
            # convert cursor → list → make ObjectId serializable
            results = list(_collection.find({}))
            for doc in results:
                doc["_id"] = str(doc["_id"])
            return results
        except PyMongoError as exc:
            print(f"[WARNING] Failed to read analyses from MongoDB: {exc}")

    # Fallback
    return list(_in_memory_store)


def get_most_recent_unprocessed_audio_file() -> Optional[tuple[str, bytes]]:
    """
    Get the most recent unprocessed audio file from GridFS.
    """
    _init_connection()

    if (
        not _db_available
        or _audio_uploads_collection is None
        or _fs is None
        or _collection is None
    ):
        print("[WARNING] Database not available, cannot get audio file")
        return None

    try:
        # Get all uploads sorted by most recent first
        all_uploads = list(_audio_uploads_collection.find().sort("upload_date", -1))

        if not all_uploads:
            print("[INFO] No audio uploads found in database")
            return None

        # Find the first upload that hasn't been analyzed yet
        for upload in all_uploads:
            file_id = upload.get("file_id")
            if file_id is None:
                continue

            if isinstance(file_id, str):
                file_id = ObjectId(file_id)

            filename = upload.get("filename", "audio.wav")

            # Check if this file has already been analyzed
            existing_analysis = _collection.find_one({"audio_path": filename})
            if existing_analysis is not None:
                print(f"[INFO] File {filename} already analyzed, skipping")
                continue

            try:
                grid_file = _fs.get(file_id)
                file_content = grid_file.read()

                print(
                    f"[INFO] Retrieved unprocessed audio file from GridFS: {filename}"
                )
                return (filename, file_content)
            except (PyMongoError, OSError) as grid_err:
                print(f"[WARNING] Failed to fetch GridFS file {file_id}: {grid_err}")
                continue

        return None

    except PyMongoError as exc:
        print(f"[WARNING] Failed to get audio file from GridFS: {exc}")
        traceback.print_exc()
        return None
