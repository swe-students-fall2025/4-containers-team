"""Machine Learning orchestrator."""

import os
import tempfile
import time
import traceback

import requests
from requests import RequestException

from language_learner import detect_language_from_audio
from database import save_result, get_most_recent_unprocessed_audio_file


def process_one_file():
    """Process a single audio file. Returns True if a file was processed, False otherwise."""
    print("[INFO] Looking for unprocessed audio in MongoDB GridFS")
    audio_data = get_most_recent_unprocessed_audio_file()

    if audio_data is None:
        return False

    filename, file_content = audio_data
    print(f"[INFO] Retrieved audio file: {filename}")

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(filename)[1]
    ) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name

    try:
        result = detect_language_from_audio(tmp_path)

        language = result.get("language", "unknown")
        transcript = result.get("transcript", "")

        print("[RESULT]")
        print(f"  language   : {language}")
        print(f"  transcript : {transcript}")

        # Send result to web-app (for display, not database storage)
        web_app_url = os.environ.get("WEB_APP_URL", "http://web-app:5000")
        try:
            response = requests.post(
                f"{web_app_url}/api/ml-result",
                json={
                    "language": language,
                    "transcript": transcript,
                    "audio_path": filename,
                },
                timeout=5,
            )
            if response.status_code == 200:
                print("[INFO] Result sent to web-app successfully.")
            else:
                print(
                    f"[WARNING] Failed to send result to web-app: {response.status_code}"
                )
        except RequestException as exc:
            print(f"[WARNING] Could not send result to web-app: {exc}")

        save_result(
            audio_path=filename,
            lang=language,
            transcript=transcript,
        )
        print("[INFO] Saved result to MongoDB.")

        return True
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main():
    """Main loop - continuously process audio files."""
    interval = int(os.environ.get("COLLECTION_INTERVAL", "5"))

    while True:
        try:
            processed = process_one_file()

            if processed:
                # File was processed, wait a bit before checking for next one
                time.sleep(5)
            else:
                # No files to process, wait longer before checking again
                print(
                    f"[INFO] No unprocessed files found. Waiting {interval} seconds..."
                )
                time.sleep(interval)
        except KeyboardInterrupt:
            print("[INFO] Shutting down...")
            break
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[ERROR] Unexpected error: {exc}")
            traceback.print_exc()
            # Wait before retrying
            time.sleep(10)


if __name__ == "__main__":
    raise SystemExit(main())
