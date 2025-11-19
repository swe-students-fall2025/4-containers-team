from flask import Flask, render_template, jsonify, request
import os
from datetime import datetime
from pathlib import Path
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from database import get_all_results, save_result

try:
    from database import fs, audio_uploads_collection, analyses_collection
except ConnectionFailure as e:
    print(f"Warning: Database connection failed at startup: {e}")
    fs = None
    audio_uploads_collection = None
    analyses_collection = None

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
default_upload = BASE_DIR / "uploads"

app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", str(default_upload))


# create folder for uploads if missing
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# In-memory cache for ML results (no database storage)
# Stores recent analysis results temporarily
ml_results_cache = []
MAX_CACHE_SIZE = 100  # Keep last 100 results


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/stats", methods=["GET"])
def get_stats():
    if audio_uploads_collection is None:
        return jsonify({"error": "database connection not available"}), 503

    try:
        total_uploads = audio_uploads_collection.count_documents({})

        return jsonify({"total_uploads": total_uploads}), 200

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500


# @app.route("/api/analyses", methods=["GET"])
# def get_analyses():
#     """Get recent analyses from the database"""
#     if analyses_collection is None:
#         return jsonify({"error": "database connection not available"}), 503

#     try:
#         # Get recent analyses, sorted by analysis_date descending
#         limit = int(request.args.get("limit", 10))
#         analyses = list(
#             analyses_collection.find({}).sort("analysis_date", -1).limit(limit)
#         )

#         # Convert ObjectId and datetime to strings for JSON
#         for analysis in analyses:
#             analysis["_id"] = str(analysis["_id"])
#             if "file_id" in analysis:
#                 analysis["file_id"] = str(analysis["file_id"])
#             if "analysis_date" in analysis:
#                 if "analysis_date" in analysis and analysis["analysis_date"]:
#                     analysis["analysis_date"] = analysis["analysis_date"].isoformat()
#                 else:
#                     analysis["analysis_date"] = None

#         return jsonify({"analyses": analyses, "total": len(analyses)})
#     except Exception as e:
#         import traceback

#         print(traceback.format_exc())
#         return jsonify({"error": f"Failed to get analyses: {str(e)}"}), 500


# @app.route("/api/ml-result", methods=["POST"])
# def receive_ml_result():
#     """Receive ML result from ML client (for display/cache only, not database storage)."""
#     try:
#         data = request.get_json(silent=True)

#         if not data:
#             return jsonify({"error": "No data provided"}), 400

#         # Add to cache for immediate display (ML client already saved to DB)
#         result = {
#             "language": data.get("language", "unknown"),
#             "transcript": data.get("transcript", ""),
#             "timestamp": datetime.now().isoformat(),
#             "audio_path": data.get("audio_path", ""),
#         }

#         # Add to cache (most recent first)
#         ml_results_cache.insert(0, result)

#         # Keep only recent results
#         if len(ml_results_cache) > MAX_CACHE_SIZE:
#             ml_results_cache.pop()

#         print(f"[INFO] Received ML result (cached): language={result['language']}")
#         return jsonify({"message": "Result received and cached", "result": result}), 200

#     except Exception as e:
#         import traceback

#         print(traceback.format_exc())
#         return jsonify({"error": f"Failed to receive result: {str(e)}"}), 500


@app.route("/api/ml-results", methods=["GET"])
def get_ml_results():
    """Fetch recent ML results from MongoDB"""
    try:
        limit = int(request.args.get("limit", 10))

        results = get_all_results()[:limit]  # local slicing

        return jsonify({"results": results, "total": len(results)}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch results: {str(e)}"}), 500


@app.route("/api/languages", methods=["GET"])
def get_language_distribution():
    """Get language distribution from in-memory cache (no database)"""
    try:
        # Count languages from cache
        language_counts = {}
        for result in ml_results_cache:
            lang = result.get("language", "unknown")
            language_counts[lang] = language_counts.get(lang, 0) + 1

        # Convert to list format, sorted by count
        language_distribution = [
            {"language": lang, "count": count}
            for lang, count in sorted(
                language_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return jsonify(
            {"languages": language_distribution, "total": len(ml_results_cache)}
        )
    except Exception as e:
        return jsonify({"error": f"Failed to get language distribution: {str(e)}"}), 500


@app.route("/api/uploads", methods=["GET"])
def get_uploads():
    """Get recent uploads from the database"""
    if audio_uploads_collection is None:
        return jsonify({"error": "database connection not available"}), 503

    try:
        # Get recent uploads, sorted by upload_date descending
        limit = int(request.args.get("limit", 10))
        uploads = list(
            audio_uploads_collection.find({}).sort("upload_date", -1).limit(limit)
        )

        # Convert ObjectId and datetime to strings for JSON
        for upload in uploads:
            upload["_id"] = str(upload["_id"])
            if "file_id" in upload:
                upload["file_id"] = str(upload["file_id"])
            if "upload_date" in upload:
                if "upload_date" in upload and upload["upload_date"]:
                    upload["upload_date"] = upload["upload_date"].isoformat()
                else:
                    upload["upload_date"] = None

        return jsonify({"uploads": uploads, "total": len(uploads)})
    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return jsonify({"error": f"Failed to get uploads: {str(e)}"}), 500


# @app.route("/api/latest-analysis", methods=["GET"])
# def get_latest_analysis():
#     """
#     Get analysis for a specific upload (identified by upload_id).
#     """
#     if audio_uploads_collection is None or analyses_collection is None:
#         return jsonify({"error": "database connection not available"}), 503

#     try:
#         # Get upload_id from query parameter
#         upload_id = request.args.get("upload_id")

#         if not upload_id:
#             # No upload_id provided - user hasn't uploaded anything
#             return jsonify({"has_upload": False})

#         # Find the specific upload by ID
#         try:
#             upload = audio_uploads_collection.find_one({"_id": ObjectId(upload_id)})
#         except Exception:
#             # Invalid ObjectId format
#             return jsonify({"has_upload": False})

#         if upload is None:
#             # Upload not found
#             return jsonify({"has_upload": False})

#         filename = upload.get("filename", "")

#         # Look for corresponding analysis by matching filename
#         analysis = analyses_collection.find_one({"audio_path": filename})

#         if analysis is None:
#             # Upload exists but analysis not ready yet
#             return jsonify(
#                 {
#                     "has_upload": True,
#                     "status": "processing",
#                     "filename": filename,
#                     "upload_id": upload_id,
#                     "upload_date": (
#                         upload.get("upload_date").isoformat()
#                         if upload.get("upload_date")
#                         else None
#                     ),
#                 }
#             )

#         # Analysis exists - return it
#         analysis["_id"] = str(analysis["_id"])
#         if "analysis_date" in analysis and analysis["analysis_date"]:
#             analysis["analysis_date"] = analysis["analysis_date"].isoformat()

#         return jsonify(
#             {
#                 "has_upload": True,
#                 "status": "completed",
#                 "filename": filename,
#                 "upload_id": upload_id,
#                 "analysis": {
#                     "language": analysis.get("language", "unknown"),
#                     "transcript": analysis.get("transcript", ""),
#                     "analysis_date": analysis.get("analysis_date"),
#                 },
#             }
#         )

#     except Exception as e:
#         import traceback

#         print(traceback.format_exc())
#         return jsonify({"error": f"Failed to get latest analysis: {str(e)}"}), 500


@app.route("/upload", methods=["POST"])
def upload_file():
    if "audio" not in request.files:
        return jsonify({"error": "no audio file"}), 400

    file = request.files["audio"]

    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    if fs is None or audio_uploads_collection is None:
        return jsonify({"error": "database connection not available"}), 503

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"audio_{timestamp}.wav"

    try:
        # Read file content
        file_content = file.read()

        # Store file in GridFS
        file_id = fs.put(
            file_content,
            filename=filename,
            content_type=file.content_type or "audio/wav",
        )

        # Store metadata in collection
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "upload_date": datetime.now(),
            "content_type": file.content_type or "audio/wav",
            "size": len(file_content),
        }

        result = audio_uploads_collection.insert_one(metadata)
        upload_id = str(result.inserted_id)

        print(
            f"[INFO] Uploaded audio file to GridFS: {filename} (ID: {file_id}, Upload ID: {upload_id})"
        )

        return (
            jsonify(
                {
                    "message": "uploaded",
                    "filename": filename,
                    "file_id": str(file_id),
                    "upload_id": upload_id,  # Return upload_id so frontend can track it
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"upload failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
