# The actual machine learning logic
import whisper
from database import save_result

model = whisper.load_model("tiny")


def detect_language_from_audio(filepath):
    result = model.transcribe(filepath)
    transcript = result.get("text", "").strip()
    lang = result.get(
        "language", "unknown"
    )  # unkown is a place holder, whisper handles the language detection

    # saves to MongoDB
    save_result(
        audio_path=filepath,
        transcript=transcript,
        lang=lang,
    )

    # this is to display for web app front end
    return {
        "language": lang,
        "transcript": transcript,
    }
