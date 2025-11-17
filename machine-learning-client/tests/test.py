"""Unit tests for machine learning client."""

import sys
import os
import main
import language_learner
import database

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import main  # pylint: disable=wrong-import-position,import-error


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
        monkeypatch.setattr(sys, "argv", ["main", "/no/such/file.wav"])
        assert main.main() != 0  # should detect missing file

    def test_main_with_valid_file(monkeypatch, tmp_path):
        # create a dummy audio file
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"fake audio")

        # make argv look like: python main.py <audio_path>
        monkeypatch.setattr(sys, "argv", ["main", str(audio_path)])

        # fake language_learner.detect_language_from_audio
        def fake_detect(path):
            assert str(path) == str(audio_path)
            return {
                "language": "en",
                "transcript": "hello world",
                "confidence": 0.9,
            }

        monkeypatch.setattr(language_learner, "detect_language_from_audio", fake_detect)

       #fix this later with real save_result implementation
        def fake_save_result(audio_path_, language, transcript, confidence=None):
            # just make sure it gets called with something reasonable
            assert language == "en"
            assert transcript == "hello world"

        monkeypatch.setattr(database, "save_result", fake_save_result)

        # now run main; it should go through the "happy path" branch
        rc = main.main()
        assert rc == 0

