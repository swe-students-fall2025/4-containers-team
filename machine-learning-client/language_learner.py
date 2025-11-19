"""Language detection helper that wraps Whisper."""

try:
    import whisper  # pylint: disable=import-error
except ImportError:
    whisper = None  # pylint: disable=invalid-name

# Only load the model if whisper is actually available.
if whisper is not None:
    model = whisper.load_model("tiny")  # pylint: disable=invalid-name
else:
    model = None  # pylint: disable=invalid-name


def detect_language_from_audio(filepath):
    """
    Detect language and transcribe audio using Whisper.
    """
    if model is None:
        # Either raise, or log & return a dummy result
        raise RuntimeError("Whisper model is not available in this environment.")

    result = model.transcribe(filepath)
    transcript = result.get("text", "").strip()
    lang = result.get(
        "language", "unknown"
    )  # unkown is a place holder, whisper handles the language detection

    return {
        "language": lang,
        "transcript": transcript,
    }
