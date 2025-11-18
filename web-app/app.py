from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
default_upload = BASE_DIR / "uploads"

app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", str(default_upload))


# create folder for uploads if missing
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "audio" not in request.files:
        return jsonify({"error": "no audio file"}), 400

    file = request.files["audio"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"audio_{timestamp}.wav"

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    return jsonify({"message": "uploaded", "filename": filename})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
