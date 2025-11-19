import os
import io
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import (
    app,
    ml_results_cache,
    MAX_CACHE_SIZE,
)

# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture(autouse=True)
def reset_cache():
    """Reset ML cache before each test."""
    ml_results_cache.clear()
    yield


@pytest.fixture(name="client")
def client_fixture():
    """Create a test client with TEMP upload folder."""
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
    with app.test_client() as test_client:
        yield test_client


# =====================================================================
# HOME ROUTE TESTS
# =====================================================================

class TestHomeRoute:
    def test_home_200(self, client):
        response = client.get("/")
        assert response.status_code == 200


# =====================================================================
# /upload TESTS
# =====================================================================

class TestUploadRoute:

    @patch("app.audio_uploads_collection")
    @patch("database.fs")
    def test_upload_no_file(self, _mock_fs, _mock_coll, client):
        resp = client.post("/upload")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no audio file"

    @patch("app.audio_uploads_collection")
    @patch("database.fs")
    def test_upload_empty_filename(self, mock_fs, mock_coll, client):
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "")})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "no file selected"

    @patch("app.audio_uploads_collection", None)
    @patch("database.fs", None)
    def test_upload_no_db(self, client):
        resp = client.post("/upload", data={"audio": (io.BytesIO(b"abc"), "x.wav")})
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_success(self, mock_fs, mock_coll, client):
        mock_fs.put = MagicMock(return_value="fake_file_id")
        mock_coll.insert_one = MagicMock(return_value=MagicMock(inserted_id="fake_upload_id"))

        resp = client.post("/upload", data={"audio": (io.BytesIO(b"DATA"), "ok.wav")})
        json = resp.get_json()

        assert resp.status_code == 200
        assert json["message"] == "uploaded"
        assert json["file_id"] == "fake_file_id"
        assert json["upload_id"] == "fake_upload_id"


# =====================================================================
# /api/stats TESTS
# =====================================================================

class TestStatsRoute:

    @patch("app.audio_uploads_collection")
    def test_stats_ok(self, mock_coll, client):
        mock_coll.count_documents.return_value = 7
        resp = client.get("/api/stats")
        assert resp.get_json()["total_uploads"] == 7
        assert resp.status_code == 200

    @patch("app.audio_uploads_collection", None)
    def test_stats_no_db(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_stats_exception(self, mock_coll, client):
        mock_coll.count_documents.side_effect = RuntimeError("boom")
        resp = client.get("/api/stats")
        assert resp.status_code == 500
        assert "Failed to get stats" in resp.get_json()["error"]


# =====================================================================
# /api/analyses TESTS
# =====================================================================

# class TestAnalyses:

#     @patch("database.analyses_collection")
#     def test_get_analyses_ok(self, mock_coll, client):
#         now = datetime.utcnow()
#         mock_coll.find.return_value.sort.return_value.limit.return_value = [
#             {"_id": 1, "file_id": 2, "analysis_date": now}
#         ]

#         resp = client.get("/api/analyses")
#         data = resp.get_json()

#         assert resp.status_code == 200
#         assert data["total"] == 1
#         assert data["analyses"][0]["analysis_date"] == now.isoformat()

#     @patch("database.analyses_collection", None)
#     def test_no_db(self, client):
#         resp = client.get("/api/analyses")
#         assert resp.status_code == 503
#         assert resp.get_json()["error"] == "database connection not available"

#     @patch("database.analyses_collection")
#     def test_exception(self, mock_coll, client):
#         mock_coll.find.side_effect = RuntimeError("fail")
#         resp = client.get("/api/analyses")
#         assert resp.status_code == 500
#         assert "Failed to get analyses" in resp.get_json()["error"]


# =====================================================================
# /api/ml-result (POST) TESTS
# =====================================================================

class TestMLResultPost:

    def test_post_success(self, client):
        payload = {"language": "english", "transcript": "hi", "audio_path": "/x.wav"}
        resp = client.post("/api/ml-result", json=payload)

        assert resp.status_code == 200
        assert len(ml_results_cache) == 1
        assert ml_results_cache[0]["language"] == "english"

    def test_missing_body(self, client):
        resp = client.post("/api/ml-result", data={})
        assert resp.status_code == 400

    def test_cache_limit(self, client):
        for i in range(MAX_CACHE_SIZE + 5):
            client.post("/api/ml-result", json={"language": "L", "transcript": "", "audio_path": ""})

        assert len(ml_results_cache) == MAX_CACHE_SIZE


# =====================================================================
# /api/ml-results TESTS
# =====================================================================

class TestMLResults:

    @patch("app.get_all_results")
    def test_ml_results_ok(self, mock_get, client):
        mock_get.return_value = [{"a": 1}, {"b": 2}]
        resp = client.get("/api/ml-results?limit=1")
        assert resp.status_code == 200
        assert len(resp.get_json()["results"]) == 1

    @patch("app.get_all_results", side_effect=RuntimeError("boom"))
    def test_ml_results_exception(self, _mock, client):
        resp = client.get("/api/ml-results")
        assert resp.status_code == 500


# =====================================================================
# /api/languages TESTS
# =====================================================================

class TestLanguageDistribution:

    def test_languages_ok(self, client):
        ml_results_cache.extend([
            {"language": "english"},
            {"language": "english"},
            {"language": "spanish"},
        ])

        resp = client.get("/api/languages")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["languages"][0]["language"] == "english"
        assert data["languages"][0]["count"] == 2

    def test_languages_exception(self, client):
        with patch("app.ml_results_cache", None):
            resp = client.get("/api/languages")
            assert resp.status_code == 500


# =====================================================================
# /api/uploads TESTS
# =====================================================================

class TestUploads:

    @patch("app.audio_uploads_collection")
    def test_uploads_ok(self, mock_coll, client):
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
        resp = client.get("/api/uploads")
        assert resp.status_code == 503
        assert resp.get_json()["error"] == "database connection not available"

    @patch("app.audio_uploads_collection")
    def test_uploads_exception(self, mock_coll, client):
        mock_coll.find.side_effect = RuntimeError("fail")
        resp = client.get("/api/uploads")
        assert resp.status_code == 500
        assert "Failed to get uploads" in resp.get_json()["error"]
