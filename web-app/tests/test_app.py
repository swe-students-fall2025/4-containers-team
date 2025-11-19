"""Unit tests for app API routes."""

import os
import sys
import io
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# pylint: disable=wrong-import-position,import-error
try:
    from app import app
except ImportError:
    ALT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
    if ALT_ROOT not in sys.path:
        sys.path.insert(0, ALT_ROOT)
    from app import app
# pylint: enable=wrong-import-position,import-error


# ================================================================
# FIXTURES
# ================================================================


@pytest.fixture(name="client")
def client_fixture():
    """Creates test client with isolated upload folder."""
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
    with app.test_client() as test_client:
        yield test_client


# ================================================================
# HOME ROUTE
# ================================================================


class TestHomeRoute:
    """Tests for home route."""

    def test_home_ok(self, client):
        """Test home route returns 200."""
        resp = client.get("/")
        assert resp.status_code == 200


# ================================================================
# /upload
# ================================================================


class TestUploadRoute:
    """Tests for upload route."""

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_no_file(self, _mock_fs, _mock_coll, client):
        """Test upload without file returns 400."""
        resp = client.post("/upload")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no audio file"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_empty_filename(self, _mock_fs, _mock_coll, client):
        """Test upload with empty filename returns 400."""
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "")})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no file selected"

    @patch("app.audio_uploads_collection", None)
    @patch("app.fs", None)
    def test_upload_no_db(self, client):
        """Test upload without database returns 503."""
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "x.wav")})
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_success(self, mock_fs, mock_coll, client):
        """Test successful upload returns 200."""
        mock_fs.put.return_value = "fake_file_id"
        mock_coll.insert_one.return_value = MagicMock(inserted_id="fake_upload_id")

        resp = client.post(
            "/upload",
            data={"audio": (io.BytesIO(b"data"), "ok.wav")},
            content_type="multipart/form-data",
        )

        data = resp.get_json()

        assert resp.status_code == 200
        assert data["message"] == "uploaded"
        assert data["file_id"] == "fake_file_id"
        assert data["upload_id"] == "fake_upload_id"


# ================================================================
# /api/stats
# ================================================================


class TestStatsRoute:
    """Tests for stats route."""

    @patch("app.audio_uploads_collection")
    def test_stats_ok(self, mock_coll, client):
        """Test stats route returns correct count."""
        mock_coll.count_documents.return_value = 7
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert resp.get_json()["total_uploads"] == 7

    @patch("app.audio_uploads_collection", None)
    def test_stats_no_db(self, client):
        """Test stats without database returns 503."""
        resp = client.get("/api/stats")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_stats_exception(self, mock_coll, client):
        """Test stats handles exceptions gracefully."""
        mock_coll.count_documents.side_effect = RuntimeError("boom")
        resp = client.get("/api/stats")
        assert resp.status_code == 500
        assert "Failed to get stats" in resp.get_json()["error"]


# ================================================================
# /api/ml-results
# ================================================================


class TestMLResults:
    """Tests for ML results route."""

    @patch("app.get_all_results")
    def test_ml_results_ok(self, mock_get, client):
        """Test ML results route returns limited results."""
        mock_get.return_value = [{"a": 1}, {"b": 2}]
        resp = client.get("/api/ml-results?limit=1")
        assert resp.status_code == 200
        assert len(resp.get_json()["results"]) == 1

    @patch("app.get_all_results", side_effect=RuntimeError("boom"))
    def test_ml_results_exception(self, _mock, client):
        """Test ML results handles exceptions gracefully."""
        resp = client.get("/api/ml-results")
        assert resp.status_code == 500


# ================================================================
# /api/languages  (cache-based)
# ================================================================


class TestLanguages:
    """Tests for languages route."""

    def test_languages_ok(self, client):
        """Test languages route returns correct counts."""
        # pylint: disable=import-outside-toplevel
        from app import ml_results_cache

        ml_results_cache.clear()
        ml_results_cache.extend(
            [
                {"language": "english"},
                {"language": "english"},
                {"language": "spanish"},
            ]
        )

        resp = client.get("/api/languages")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["languages"][0]["language"] == "english"
        assert data["languages"][0]["count"] == 2

    def test_languages_exception(self, client):
        """Test languages handles exceptions gracefully."""
        with patch("app.ml_results_cache", None):
            resp = client.get("/api/languages")
            assert resp.status_code == 500


# ================================================================
# /api/uploads
# ================================================================


class TestUploads:
    """Tests for uploads route."""

    @patch("app.audio_uploads_collection")
    def test_uploads_ok(self, mock_coll, client):
        """Test uploads route returns correct data."""
        now = datetime.utcnow()
        mock_coll.find.return_value.sort.return_value.limit.return_value = [
            {"_id": 1, "file_id": 2, "upload_date": now}
        ]

        resp = client.get("/api/uploads")
        json_data = resp.get_json()

        assert resp.status_code == 200
        assert json_data["total"] == 1
        assert json_data["uploads"][0]["upload_date"] == now.isoformat()

    @patch("app.audio_uploads_collection", None)
    def test_uploads_no_db(self, client):
        """Test uploads without database returns 503."""
        resp = client.get("/api/uploads")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_uploads_exception(self, mock_coll, client):
        """Test uploads handles exceptions gracefully."""
        mock_coll.find.side_effect = RuntimeError("fail")
        resp = client.get("/api/uploads")
        assert resp.status_code == 500
        assert "Failed to get uploads" in resp.get_json()["error"]
