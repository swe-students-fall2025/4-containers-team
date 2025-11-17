"""Unit tests for machine learning client."""

import sys
import os
import main
import language_learner
import database

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_detect_language_from_audio_uses_model_and_saves(monkeypatch, tmp_path):
    """detect_language_from_audio should call the model and save_result."""
    audio_path = tmp_path / "dummy.wav"
    audio_path.write_bytes(b"fake audio bytes")

    class DummyModel:
        """Fake Whisper model for testing."""

        def transcribe(self, path: str) -> dict[str, object]:
            assert str(path) == str(audio_path)
            return {
                "text": "bonjour",
                "language": "fr",
                "avg_logprob": -0.2,
            }
 
    language_learner.model = DummyModel()

    saved: dict[str, object] = {}

    def fake_save_result(
        audio_path_: str, language: str, transcript: str, confidence: float | None = None
    ) -> None:
        """Fake DB save, just records the values in a dict."""
        saved["audio_path"] = str(audio_path_)
        saved["language"] = language
        saved["transcript"] = transcript
        saved["confidence"] = confidence

    monkeypatch.setattr(database, "save_result", fake_save_result)

    result = language_learner.detect_language_from_audio(str(audio_path))

    assert result["language"] == "fr"
    assert result["transcript"] == "bonjour"
    assert "confidence" in result

    assert saved["audio_path"] == str(audio_path)
    assert saved["language"] == "fr"
    assert saved["transcript"] == "bonjour"
    assert saved["confidence"] is not None


class TestMain:
    """Tests for main module."""

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        assert callable(main)

    def test_main_runs_without_error(self):
        """Test that main function runs without error."""
        main()
        assert True

    def test_main_nonexistent_file(monkeypatch):
        """main.main should fail when given a non-existent file."""
        monkeypatch.setattr(sys, "argv", ["main", "/no/such/file.wav"])
        assert main.main() != 0


    def test_main_with_valid_file(monkeypatch, tmp_path):
        """main.main should succeed and call detect_language_from_audio + save_result."""
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"fake audio")

        monkeypatch.setattr(sys, "argv", ["main", str(audio_path)])

        def fake_detect(path: str) -> dict[str, object]:
            assert str(path) == str(audio_path)
            return {
                "language": "en",
                "transcript": "hello world",
            }

        monkeypatch.setattr(language_learner, "detect_language_from_audio", fake_detect)

        called: dict[str, object] = {}

        def fake_save_result(
            audio_path_: str, language: str, transcript: str | None = None
        ) -> None:
            """Fake DB save for main.main test."""
            called["audio_path"] = str(audio_path_)
            called["language"] = language
            called["transcript"] = transcript

        monkeypatch.setattr(database, "save_result", fake_save_result)

        rc = main.main()
        assert rc == 0
        assert called["audio_path"] == str(audio_path)
        assert called["language"] == "en"
        assert called["transcript"] == "hello world"

"""
tests for language_learning.py
"""

