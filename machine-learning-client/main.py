"""Machine Learning orchestrator."""

import os
import sys
from datetime import datetime
import requests

from language_learner import detect_language_from_audio
from database import save_result


upload_dir = "/uploads"


def find_most_recent_audio(upload_dir: str) -> str | None:
    # Return the full path of the most recently modified audio file, or None.
    if not os.path.isdir(upload_dir):
        print(f"[ERROR] Upload directory does not exist: {upload_dir}")
        return None

    files = []
    for name in os.listdir(upload_dir):
        # only look at wav/webm files
        if name.lower().endswith((".wav", ".webm", ".mp3", ".m4a", ".ogg")):
            full_path = os.path.join(upload_dir, name)
            if os.path.isfile(full_path):
                files.append(full_path)

    if not files:
        print(f"[INFO] No audio files found in {upload_dir}")
        return None

    # pick the newest by modification time
    latest = max(files, key=os.path.getmtime)
    return latest


def main() -> int:
    print(f"[INFO] Looking for latest audio in: {upload_dir}")
    audio_path = find_most_recent_audio(upload_dir)

    if audio_path is None:
        return 1

    print(f"[INFO] Using most recent audio file: {audio_path}")

    result = detect_language_from_audio(audio_path)

    language = result.get("language", "unknown")
    transcript = result.get("transcript", "")

    print("[RESULT]")
    print(f"  language   : {language}")
    print(f"  transcript : {transcript}")

    # Send result to web-app (no database storage)
    web_app_url = os.environ.get("WEB_APP_URL", "http://web-app:5000")
    try:
        response = requests.post(
            f"{web_app_url}/api/ml-result",
            json={
                "language": language,
                "transcript": transcript,
                "audio_path": audio_path,
            },
            timeout=5,
        )
        if response.status_code == 200:
            print("[INFO] Result sent to web-app successfully.")
        else:
            print(f"[WARNING] Failed to send result to web-app: {response.status_code}")
    except Exception as e:
        print(f"[WARNING] Could not send result to web-app: {e}")

    save_result(
        audio_path=audio_path,
        lang=language,
        transcript=transcript,
    )
    print("[INFO] Saved result to MongoDB.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
