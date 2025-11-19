# pylint: disable=R0903,too-few-public-methods
"""Unit tests for app API routes."""

import os
import io
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

# Ensure project root on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app, ml_results_cache, MAX_CACHE_SIZE  # noqa


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture(autouse=True)
def reset_cache():
    """Reset ML results cache before every test."""
    ml_results_cache.clear()
    yield


@pytest.fixture(name="client")
def client_fixture():
    """Create test client with a temporary upload folder."""
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
    with app.test_client() as test_client:
        yield test_client


# =====================================================================
# HOME ROUTE
# =====================================================================

class TestHomeRoute:
    """Tests for the home route."""

    def test_home_200(self, client):
        """GET / should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200


# =====================================================================
# /upload
# =====================================================================

class TestUploadRoute:
    """Tests for the /upload route."""

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_no_file(self, _mock_fs, _mock_coll, client):
        """Uploading without a file should return 400."""
        resp = client.post("/upload")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no audio file"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_empty_filename(self, _mock_fs, _mock_coll, client):
        """Upload with empty filename should return 400."""
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "")})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no file selected"

    @patch("app.audio_uploads_collection", None)
    @patch("app.fs", None)
    def test_upload_no_db(self, client):
        """If DB is missing, return 503."""
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "x.wav")})
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_success(self, mock_fs, mock_coll, client):
        """Successful upload should return file + upload IDs."""
        mock_fs.put = MagicMock(return_value="fake_file_id")
        mock_coll.insert_one = MagicMock(
            return_value=MagicMock(inserted_id="fake_upload_id")
        )

        resp = client.post("/upload", data={"audio": (io.BytesIO(b"DATA"), "ok.wav")})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["message"] == "uploaded"
        assert data["file_id"] == "fake_file_id"
        assert data["upload_id"] == "fake_upload_id"


# =====================================================================
# /api/stats
# =====================================================================

class TestStatsRoute:
    """Tests for /api/stats."""

    @patch("app.audio_uploads_collection")
    def test_stats_ok(self, mock_coll, client):
        """Should return total uploads count."""
        mock_coll.count_documents.return_value = 7
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert resp.get_json()["total_uploads"] == 7

    @patch("app.audio_uploads_collection", None)
    def test_stats_no_db(self, client):
        """Missing DB should return 503."""
        resp = client.get("/api/stats")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_stats_exception(self, mock_coll, client):
        """Exception should return 500."""
        mock_coll.count_documents.side_effect = RuntimeError("boom")
        resp = client.get("/api/stats")
        assert resp.status_code == 500
        assert "Failed to get stats" in resp.get_json()["error"]


# =====================================================================
# /api/ml-result (POST)
# =====================================================================

class TestMLResultPost:
    """Tests for POST /api/ml-result."""

    def test_post_success(self, client):
        """Posting ML result should insert into cache."""
        body = {"language": "english", "transcript": "hi", "audio_path": "/x.wav"}
        resp = client.post("/api/ml-result", json=body)

        assert resp.status_code == 200
        assert len(ml_results_cache) == 1
        assert ml_results_cache[0]["language"] == "english"

    def test_missing_body(self, client):
        """Missing JSON body should return 400."""
        resp = client.post("/api/ml-result", data={})
        assert resp.status_code == 400

    def test_cache_limit(self, client):
        """Cache should not exceed MAX_CACHE_SIZE."""
        for _ in range(MAX_CACHE_SIZE + 5):
            client.post(
                "/api/ml-result",
                json={"language": "x", "transcript": "", "audio_path": ""},
            )

        assert len(ml_results_cache) == MAX_CACHE_SIZE


# =====================================================================
# /api/ml-results
# =====================================================================

class TestMLResults:
    """Tests for GET /api/ml-results."""

    @patch("app.get_all_results")
    def test_ml_results_ok(self, mock_get, client):
        """Should return limited results."""
        mock_get.return_value = [{"a": 1}, {"b": 2}]
        resp = client.get("/api/ml-results?limit=1")

        assert resp.status_code == 200
        assert len(resp.get_json()["results"]) == 1

    @patch("app.get_all_results", side_effect=RuntimeError("boom"))
    def test_ml_results_exception(self, _mock, client):
        """Exceptions should return 500."""
        resp = client.get("/api/ml-results")
        assert resp.status_code == 500


# =====================================================================
# /api/languages
# =====================================================================

class TestLanguageDistribution:
    """Tests for GET /api/languages."""

    def test_languages_ok(self, client):
        """Should return language counts."""
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
        """If cache missing, return 500."""
        with patch("app.ml_results_cache", None):
            resp = client.get("/api/languages")
            assert resp.status_code == 500


# =====================================================================
# /api/uploads
# =====================================================================

class TestUploads:
    """Tests for GET /api/uploads."""

    @patch("app.audio_uploads_collection")
    def test_uploads_ok(self, mock_coll, client):
        """Should return uploads list."""
        now = datetime.utcnow()
        mock_coll.find.return_value.sort.return_value.limit.return_value = [
            {"_id": 1, "file_id": 2, "upload_date": now}
        ]

        resp = client.get("/api/uploads")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["total"] == 1
        assert data["uploads"][0]["upload_date"] == now.isoformat()

    @patch("app.audio_uploads_collection", None)
    def test_uploads_no_db(self, client):
        """Missing DB should return 503."""
        resp = client.get("/api/uploads")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_uploads_exception(self, mock_coll, client):
        """Exception should return 500."""
        mock_coll.find.side_effect = RuntimeError("fail")
        resp = client.get("/api/uploads")
        assert resp.status_code == 500
        assert "Failed to get uploads" in resp.get_json()["error"]
