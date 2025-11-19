# pylint: disable=R0903
"""Unit tests for app API routes."""

import os
import sys
import io
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

try:
    from app import app, ml_results_cache
except ImportError:
    ALT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
    sys.path.insert(0, ALT_ROOT)
    from app import app, ml_results_cache


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
    """Unit tests for the home route."""

    def test_home_ok(self, client):
        """Tests home route."""
        resp = client.get("/")
        assert resp.status_code == 200


# ================================================================
# /upload
# ================================================================


class TestUploadRoute:
    """Unit tests for the upload route."""

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_no_file(self, _mock_fs, _mock_coll, client):
        """Tests uploading with no file."""
        resp = client.post("/upload")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no audio file"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_empty_filename(self, _mock_fs, _mock_coll, client):
        """Tests uploading to audio uploads collection."""
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "")})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no file selected"

    @patch("app.audio_uploads_collection", None)
    @patch("app.fs", None)
    def test_upload_no_db(self, client):
        """Tests uploading to database failed"""
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "x.wav")})
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_success(self, mock_fs, mock_coll, client):
        """Tests successful upload."""
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
    """Unit tests for the stats route."""

    @patch("app.audio_uploads_collection")
    def test_stats_ok(self, mock_coll, client):
        """Tests count of audio uploads"""
        mock_coll.count_documents.return_value = 7
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert resp.get_json()["total_uploads"] == 7

    @patch("app.audio_uploads_collection", None)
    def test_stats_no_db(self, client):
        """Tests count without database."""
        resp = client.get("/api/stats")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_stats_exception(self, mock_coll, client):
        """Tests error exception for statistics"""
        mock_coll.count_documents.side_effect = RuntimeError("boom")
        resp = client.get("/api/stats")
        assert resp.status_code == 500
        assert "Failed to get stats" in resp.get_json()["error"]


# ================================================================
# /api/ml-results (GET)
# ================================================================


class TestMLResults:
    """Unit tests for the ml-results route."""

    @patch("app.get_all_results")
    def test_ml_results_ok(self, mock_get, client):
        """Tests correct results"""
        mock_get.return_value = [{"a": 1}, {"b": 2}]
        resp = client.get("/api/ml-results?limit=1")
        assert resp.status_code == 200
        assert len(resp.get_json()["results"]) == 1

    @patch("app.get_all_results", side_effect=RuntimeError("boom"))
    def test_ml_results_exception(self, _mock, client):
        """Tests exception for retrieving results"""
        resp = client.get("/api/ml-results")
        assert resp.status_code == 500


# ================================================================
# /api/languages
# ================================================================


class TestLanguages:
    """Unit tests for the languages route."""

    def test_languages_ok(self, client):
        """Tests language detection correctly"""

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
        """Tests language detection with exception"""
        with patch("app.ml_results_cache", None):
            resp = client.get("/api/languages")
            assert resp.status_code == 500


# ================================================================
# /api/uploads
# ================================================================


class TestUploads:
    """Unit tests for the retrieving uploads route."""

    @patch("app.audio_uploads_collection")
    def test_uploads_ok(self, mock_coll, client):
        """Tests retrieving from uploads correctly"""
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
        """Tests retrieving from uploads with no database"""
        resp = client.get("/api/uploads")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_uploads_exception(self, mock_coll, client):
        """Tests retrieving from uploads with exception"""
        mock_coll.find.side_effect = RuntimeError("fail")
        resp = client.get("/api/uploads")
        assert resp.status_code == 500
        assert "Failed to get uploads" in resp.get_json()["error"]


# ================================================================
# /api/analyses
# ================================================================


class TestGetAnalysesRoute:
    """Unit tests for the analyses route."""

    @patch("app.analyses_collection")
    def test_get_analyses_no_db(self, _mock_coll, client):
        """If analyses_collection is None return 503."""
        with patch("app.analyses_collection", None):
            resp = client.get("/api/analyses")
            assert resp.status_code == 503
            assert resp.get_json()["error"] == "database connection not available"

    @patch("app.analyses_collection")
    def test_get_analyses_success(self, mock_coll, client):
        """Tests successful retrieval and conversion of fields."""

        # Simulate Mongo cursor chain: find().sort().limit()
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = [
            {
                "_id": MagicMock(__str__=lambda self="x": "abc123"),
                "file_id": MagicMock(__str__=lambda self="x": "file456"),
                "analysis_date": datetime(2024, 1, 1, 12, 0, 0),
            }
        ]

        mock_coll.find.return_value = mock_cursor

        resp = client.get("/api/analyses?limit=1")
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["total"] == 1
        item = data["analyses"][0]

        assert item["_id"] == "abc123"
        assert item["file_id"] == "file456"
        assert item["analysis_date"] == "2024-01-01T12:00:00"

    @patch("app.analyses_collection")
    def test_get_analyses_exception(self, mock_coll, client):
        """If an exception occurs, return 500."""

        mock_coll.find.side_effect = Exception("DB error")

        resp = client.get("/api/analyses")
        assert resp.status_code == 500

        data = resp.get_json()
        assert "Failed to get analyses" in data["error"]
        assert "DB error" in data["error"]


# ================================================================
# /api/ml-result  (POST)
# ================================================================


class TestMLResultPost:
    """Unit tests for ml result POST"""

    @patch("app.ml_results_cache")
    def test_ml_result_no_data(self, mock_cache, client):
        """Tests posting with no JSON body."""
        resp = client.post("/api/ml-result")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "No data provided"

    @patch("app.ml_results_cache")
    def test_ml_result_success(self, mock_cache, client):
        """Test a successful result retrieval"""
        # Patch MAX_CACHE_SIZE inside the test (NOT as decorator)
        with patch("app.MAX_CACHE_SIZE", 5):

            mock_cache.insert = MagicMock()
            mock_cache.__len__.return_value = 0  # no trimming needed

            payload = {
                "language": "english",
                "transcript": "hello world",
                "audio_path": "/path/a.wav",
            }

            resp = client.post("/api/ml-result", json=payload)
            data = resp.get_json()

            assert resp.status_code == 200
            assert data["message"] == "Result received and cached"
            assert data["result"]["language"] == "english"
            assert data["result"]["transcript"] == "hello world"
            assert data["result"]["audio_path"] == "/path/a.wav"

            mock_cache.insert.assert_called_once()
            args, _ = mock_cache.insert.call_args
            assert args[0] == 0

    @patch("app.ml_results_cache")
    def test_ml_result_exception(self, mock_cache, client):
        """Tests exception handling during ML result processing."""

        mock_cache.insert.side_effect = RuntimeError("boom")

        payload = {"language": "english"}
        resp = client.post("/api/ml-result", json=payload)

        assert resp.status_code == 500
        assert "Failed to receive result" in resp.get_json()["error"]
