"""Tests for the machine-learning client."""

import os
import main
import language_learner
import database


# ---------------------------------------------------------------------------
# Tests for find_most_recent_audio
# ---------------------------------------------------------------------------


def test_find_most_recent_audio_empty_dir_returns_none(tmp_path):
    """If the upload directory is empty, find_most_recent_audio returns None."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    result = main.find_most_recent_audio(str(upload_dir))

    assert result is None


def test_find_most_recent_audio_picks_newest_audio_file(tmp_path):
    """find_most_recent_audio returns path of most recently modified audio file."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    old = upload_dir / "old.wav"
    new = upload_dir / "new.mp3"

    old.write_bytes(b"old")
    new.write_bytes(b"new")

    # Make sure old has an older mtime than new
    os.utime(old, (1, 1))

    result = main.find_most_recent_audio(str(upload_dir))

    assert result is not None
    assert result.endswith("new.mp3")


# ---------------------------------------------------------------------------
# Tests for language_learner.detect_language_from_audio
# ---------------------------------------------------------------------------


def test_detect_language_from_audio_calls_model_and_save_result(tmp_path):
    """detect_language_from_audio should use the model and call save_result."""
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio bytes")

    class DummyModel:  # pylint: disable=too-few-public-methods
        """Fake Whisper model for testing."""

        def transcribe(self, path):
            assert str(path) == str(audio_path)
            return {
                "text": "bonjour",
                "language": "fr",
                "avg_logprob": -0.2,
            }

    # Replace the real Whisper model with our dummy.
    language_learner.model = DummyModel()

    saved: dict[str, object] = {}

    def fake_save_result(**kwargs):
        """Fake database save; just records the kwargs."""
        saved.update(kwargs)

    language_learner.save_result = fake_save_result

    result = language_learner.detect_language_from_audio(str(audio_path))

    assert result["language"] == "fr"
    assert result["transcript"] == "bonjour"

    # Ensure we attempted to save the right info.
    assert saved["audio_path"] == str(audio_path)
    assert saved["lang"] == "fr"
    assert saved["transcript"] == "bonjour"


# ---------------------------------------------------------------------------
# Tests for main.main orchestrator
# ---------------------------------------------------------------------------


def test_main_returns_1_when_no_audio_files(tmp_path, monkeypatch):
    """main.main returns 1 when no audio files are present in the upload dir."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    # Use our empty directory as the upload dir.
    monkeypatch.setattr(main, "UPLOAD_DIR", str(upload_dir))

    exit_code = main.main()

    assert exit_code == 1


def test_main_happy_path_with_audio(monkeypatch, tmp_path):
    """main.main returns 0 and calls detect_language_from_audio + save_result."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    audio_file = upload_dir / "recording.webm"
    audio_file.write_bytes(b"fake audio")

    # Ensure this is seen as the newest audio file.
    os.utime(audio_file, (10, 10))

    monkeypatch.setattr(main, "UPLOAD_DIR", str(upload_dir))

    def fake_detect_language_from_audio(path):
        assert str(path) == str(audio_file)
        return {
            "language": "en",
            "transcript": "hello world",
        }

    monkeypatch.setattr(
        main, "detect_language_from_audio", fake_detect_language_from_audio
    )

    saved: dict[str, object] = {}

    def fake_save_result(**kwargs):
        """Fake database save; just records kwargs from main.main."""
        saved.update(kwargs)

    monkeypatch.setattr(main, "save_result", fake_save_result)

    exit_code = main.main()

    assert exit_code == 0
    assert saved["audio_path"] == str(audio_file)
    # Note: your code uses 'lang' as the kwarg name.
    assert saved["lang"] == "en"
    assert saved["transcript"] == "hello world"


# ---------------------------------------------------------------------------
# Tests for database.save_result stub
# ---------------------------------------------------------------------------


def test_database_save_result_is_callable():
    """database.save_result should accept arguments and not raise."""
    database.save_result(
        audio_path="some/path.wav",
        language="en",
        transcript="hello world",
    )
