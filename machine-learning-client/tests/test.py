"""Unit tests for the machine-learning client."""

from __future__ import annotations

import os

import pytest
import requests

import main
import language_learner
import database


class DummyResponse:  # pylint: disable=too-few-public-methods
    """Simple response stub to fake requests.post."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


def test_process_one_file_returns_false_when_no_audio(monkeypatch):
    """process_one_file should return False when nothing is available."""

    monkeypatch.setattr(main, "get_most_recent_unprocessed_audio_file", lambda: None)

    assert main.process_one_file() is False


def test_process_one_file_processes_audio(monkeypatch):
    """When audio exists, process_one_file should save and send results."""

    fake_audio = b"fake audio bytes"
    monkeypatch.setattr(
        main,
        "get_most_recent_unprocessed_audio_file",
        lambda: ("sample.wav", fake_audio),
    )

    captured_detection: dict[str, object] = {}

    def fake_detect(temp_path):
        assert os.path.exists(temp_path)
        with open(temp_path, "rb") as tmp:
            assert tmp.read() == fake_audio
        captured_detection["path"] = temp_path
        return {"language": "en", "transcript": "hello"}

    monkeypatch.setattr(main, "detect_language_from_audio", fake_detect)

    saved_docs: dict[str, object] = {}

    def fake_save_result(**kwargs):
        saved_docs.update(kwargs)

    monkeypatch.setattr(main, "save_result", fake_save_result)

    post_calls = {"count": 0}

    def fake_post(url, json, timeout):
        assert "api/ml-result" in url
        assert json["language"] == "en"
        assert json["transcript"] == "hello"
        assert timeout == 5
        post_calls["count"] += 1
        return DummyResponse(200)

    monkeypatch.setattr(main.requests, "post", fake_post)

    assert main.process_one_file() is True
    assert post_calls["count"] == 1
    assert saved_docs["audio_path"] == "sample.wav"
    assert saved_docs["lang"] == "en"
    assert saved_docs["transcript"] == "hello"
    assert not os.path.exists(captured_detection["path"])


def test_process_one_file_handles_request_exception(monkeypatch):
    """A RequestException should be caught without stopping processing."""

    fake_audio = b"bytes"
    monkeypatch.setattr(
        main,
        "get_most_recent_unprocessed_audio_file",
        lambda: ("sample.wav", fake_audio),
    )
    monkeypatch.setattr(
        main,
        "detect_language_from_audio",
        lambda *_: {"language": "en", "transcript": "hello"},
    )

    saved_docs: dict[str, object] = {}
    monkeypatch.setattr(main, "save_result", lambda **kwargs: saved_docs.update(kwargs))

    def fake_post(*_, **__):
        raise requests.RequestException("network down")

    monkeypatch.setattr(main.requests, "post", fake_post)

    # Force os.unlink to raise so we cover that branch as well.
    monkeypatch.setattr(os, "unlink", lambda *_: (_ for _ in ()).throw(OSError()))

    assert main.process_one_file() is True
    assert saved_docs["audio_path"] == "sample.wav"


def test_main_handles_keyboard_interrupt(monkeypatch):
    """The main loop should exit cleanly when interrupted."""

    call_tracker = {"count": 0}

    def fake_process():
        call_tracker["count"] += 1
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "process_one_file", fake_process)
    monkeypatch.setattr(main.time, "sleep", lambda *_: None)

    main.main()
    assert call_tracker["count"] == 1


def test_detect_language_from_audio_with_model(monkeypatch, tmp_path):
    """detect_language_from_audio should use the configured Whisper model."""

    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"audio-bytes")

    class DummyModel:  # pylint: disable=too-few-public-methods
        def transcribe(self, filepath):
            assert str(filepath) == str(audio_path)
            return {"text": "ciao", "language": "it"}

    monkeypatch.setattr(language_learner, "model", DummyModel())

    result = language_learner.detect_language_from_audio(str(audio_path))
    assert result == {"language": "it", "transcript": "ciao"}


def test_detect_language_from_audio_without_model(monkeypatch, tmp_path):
    """When no model is loaded, detect_language_from_audio should raise."""

    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"audio-bytes")
    monkeypatch.setattr(language_learner, "model", None)

    with pytest.raises(RuntimeError):
        language_learner.detect_language_from_audio(str(audio_path))


def test_database_save_result_returns_identifier():
    """database.save_result should return an identifier even without Mongo."""

    inserted_id = database.save_result(
        audio_path="some/path.wav",
        lang="en",
        transcript="hello world",
    )
    assert inserted_id is not None


# ---------------------------------------------------------------------------
# Additional database coverage tests
# ---------------------------------------------------------------------------


def test_get_most_recent_unprocessed_audio_handles_missing_db(monkeypatch):
    """If Mongo is unavailable, the helper should return None."""

    monkeypatch.setattr(database, "_db_available", False)
    monkeypatch.setattr(database, "_audio_uploads_collection", None)
    monkeypatch.setattr(database, "_fs", None)
    monkeypatch.setattr(database, "_collection", None)

    assert database.get_most_recent_unprocessed_audio_file() is None


def test_main_sleeps_after_success(monkeypatch):
    """When work is processed, main should sleep for the short interval."""

    state = {"calls": 0}

    def fake_process():
        state["calls"] += 1
        if state["calls"] == 1:
            return True
        raise KeyboardInterrupt

    sleeps: list[int] = []
    monkeypatch.setattr(main, "process_one_file", fake_process)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(main.os, "environ", {"COLLECTION_INTERVAL": "60"})

    main.main()

    assert 5 in sleeps  # processed branch


def test_main_waits_when_no_files(monkeypatch):
    """If no files exist, main should sleep for the configured interval."""

    state = {"calls": 0}

    def fake_process():
        state["calls"] += 1
        if state["calls"] == 1:
            return False
        raise KeyboardInterrupt

    sleeps: list[int] = []
    monkeypatch.setattr(main, "process_one_file", fake_process)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(main.os, "environ", {"COLLECTION_INTERVAL": "10"})

    main.main()

    assert 10 in sleeps  # interval branch


def test_main_handles_unexpected_exception(monkeypatch):
    """Unexpected exceptions should be logged and trigger the retry sleep."""

    state = {"calls": 0}

    def fake_process():
        state["calls"] += 1
        if state["calls"] == 1:
            raise ValueError("boom")
        raise KeyboardInterrupt

    sleeps: list[int] = []
    monkeypatch.setattr(main, "process_one_file", fake_process)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(main.os, "environ", {"COLLECTION_INTERVAL": "1"})

    main.main()

    assert 10 in sleeps  # error backoff
