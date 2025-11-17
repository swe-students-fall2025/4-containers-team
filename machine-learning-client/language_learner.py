# The actual machine learning logic
from database import save_result
try:
    import whisper  
except Exception:  
    whisper = None  

# Only load the model if whisper is actually available.
if whisper is not None:
    model = whisper.load_model("tiny")
else:
    model = None


def detect_language_from_audio(filepath):
    if model is None:
    # Either raise, or log & return a dummy result
        raise RuntimeError("Whisper model is not available in this environment.")
    
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
