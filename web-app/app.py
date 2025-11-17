from flask import Flask, render_template, jsonify, request
import os
from datetime import datetime
from pymongo.errors import ConnectionFailure
try:
    from database import fs, audio_uploads_collection, analyses_collection
except ConnectionFailure as e:
    print(f"Warning: Database connection failed at startup: {e}")
    fs = None
    audio_uploads_collection = None
    analyses_collection = None

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

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
    """Get statistics: total uploads and total analyses (from cache, no database)"""
    if audio_uploads_collection is None:
        return jsonify({"error": "database connection not available"}), 503
    
    try:
        total_uploads = audio_uploads_collection.count_documents({})
        # Get analyses count from in-memory cache (no database)
        total_analyses = len(ml_results_cache)
        
        return jsonify({
            "total_uploads": total_uploads,
            "total_analyses": total_analyses
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500


@app.route("/api/analyses", methods=["GET"])
def get_analyses():
    """Get recent analyses from the database"""
    if analyses_collection is None:
        return jsonify({"error": "database connection not available"}), 503
    
    try:
        # Get recent analyses, sorted by analysis_date descending
        limit = int(request.args.get("limit", 10))
        analyses = list(analyses_collection.find({}).sort("analysis_date", -1).limit(limit))
        
        # Convert ObjectId and datetime to strings for JSON
        for analysis in analyses:
            analysis["_id"] = str(analysis["_id"])
            if "file_id" in analysis:
                analysis["file_id"] = str(analysis["file_id"])
            if "analysis_date" in analysis:
                analysis["analysis_date"] = analysis["analysis_date"].isoformat()
        
        return jsonify({
            "analyses": analyses,
            "total": len(analyses)
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to get analyses: {str(e)}"}), 500


@app.route("/api/ml-result", methods=["POST"])
def receive_ml_result():
    """Receive ML analysis result from ML client (no database storage)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Add timestamp
        result = {
            "language": data.get("language", "unknown"),
            "transcript": data.get("transcript", ""),
            "timestamp": datetime.now().isoformat(),
            "audio_path": data.get("audio_path", "")
        }
        
        # Add to cache (most recent first)
        ml_results_cache.insert(0, result)
        
        # Keep only recent results
        if len(ml_results_cache) > MAX_CACHE_SIZE:
            ml_results_cache.pop()
        
        print(f"[INFO] Received ML result: language={result['language']}")
        return jsonify({"message": "Result received", "result": result}), 200
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to receive result: {str(e)}"}), 500


@app.route("/api/ml-results", methods=["GET"])
def get_ml_results():
    """Get recent ML results from cache (no database)"""
    try:
        limit = int(request.args.get("limit", 10))
        results = ml_results_cache[:limit]
        
        return jsonify({
            "results": results,
            "total": len(ml_results_cache)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get results: {str(e)}"}), 500


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
            for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return jsonify({
            "languages": language_distribution,
            "total": len(ml_results_cache)
        })
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
        uploads = list(audio_uploads_collection.find({}).sort("upload_date", -1).limit(limit))
        
        # Convert ObjectId and datetime to strings for JSON
        for upload in uploads:
            upload["_id"] = str(upload["_id"])
            if "file_id" in upload:
                upload["file_id"] = str(upload["file_id"])
            if "upload_date" in upload:
                upload["upload_date"] = upload["upload_date"].isoformat()
        
        return jsonify({
            "uploads": uploads,
            "total": len(uploads)
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to get uploads: {str(e)}"}), 500

@app.route("/upload", methods=["POST"])
def upload_file():
    if "audio" not in request.files:
        return jsonify({"error": "no audio file"}), 400

    file = request.files["audio"]
    
    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    # Check if database is connected
    if fs is None or audio_uploads_collection is None:
        return jsonify({"error": "database connection not available"}), 503

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"audio_{timestamp}.wav"

    try:
        # Read file content
        file_content = file.read()
        
        # Store file in GridFS
        file_id = fs.put(
            file_content,
            filename=filename,
            content_type=file.content_type or "audio/wav"
        )
        
        # Store metadata in collection
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "upload_date": datetime.now(),
            "content_type": file.content_type or "audio/wav",
            "size": len(file_content)
        }

        audio_uploads_collection.insert_one(metadata)
        
        return jsonify({
            "message": "uploaded",
            "filename": filename,
            "file_id": str(file_id)
        }), 200
    except ConnectionFailure as e:
        return jsonify({"error": f"database connection failed: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"error": f"upload failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
