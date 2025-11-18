"""Machine Learning orchestrator."""

import os
import sys
from datetime import datetime

from language_learner import detect_language_from_audio
from database import save_result


upload_dir = "/uploads"


def find_most_recent_audio() -> str | None:
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
    audio_path = find_most_recent_audio()

    if audio_path is None:
        return 1

    print(f"[INFO] Using most recent audio file: {audio_path}")

    result = detect_language_from_audio(audio_path)

    language = result.get("language", "unknown")
    transcript = result.get("transcript", "")

    print("[RESULT]")
    print(f"  language   : {language}")
    print(f"  transcript : {transcript}")

    # 2) save to MongoDB

    save_result(
        audio_path=audio_path,
        lang=language,
        transcript=transcript,
    )
    print("[INFO] Saved result to MongoDB.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
