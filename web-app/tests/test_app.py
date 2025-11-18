import io
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Ensure app.py is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, ml_results_cache
from datetime import datetime


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset ML cache before each test."""
    ml_results_cache.clear()
    yield


@pytest.fixture
def client():
    """Create a test client with temp upload folder."""
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
    with app.test_client() as test_client:
        yield test_client


# ----------------------------------------------------------------------
# HOME ROUTE TESTS
# ----------------------------------------------------------------------
class TestHomeRoute:
    def test_home_route_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_home_route_renders_template(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"<html" in response.data or b"World Tour" in response.data


# ----------------------------------------------------------------------
# UPLOAD ROUTE TESTS
# ----------------------------------------------------------------------
class TestUploadRoute:
    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_without_file_returns_400(self, mock_fs, mock_coll, client):
        response = client.post("/upload")
        assert response.status_code == 400
        assert response.get_json()["error"] == "no audio file"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_with_file_success(self, mock_fs, mock_coll, client):
        mock_fs.put = MagicMock(return_value="fake_id")
        mock_coll.insert_one = MagicMock()

        audio_data = b"fake audio"
        data = {"audio": (io.BytesIO(audio_data), "test.wav")}

        response = client.post("/upload", data=data)
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["message"] == "uploaded"
        assert json_data["filename"].startswith("audio_")
        assert json_data["file_id"] == "fake_id"

    @patch("app.audio_uploads_collection")
    @patch("app.fs")
    def test_upload_gridfs_called(self, mock_fs, mock_coll, client):
        audio_data = b"12345"
        data = {"audio": (io.BytesIO(audio_data), "upload.wav")}
        mock_fs.put = MagicMock(return_value="fake_id")
        mock_coll.insert_one = MagicMock()

        client.post("/upload", data=data)

        mock_fs.put.assert_called_once()
        mock_coll.insert_one.assert_called_once()

    def test_upload_file_selected_empty_filename_returns_400(self, client):
        # Simulate uploaded file with empty filename
        data = {"audio": (io.BytesIO(b"abc"), "")}
        response = client.post("/upload", data=data)
        # Because the app checks file.filename == "" -> 400
        assert response.status_code == 400
        assert response.get_json()["error"] == "no file selected"

    def test_upload_db_unavailable_returns_503(self, client):
        # Provide file but DB handles are None
        with patch("app.fs", None), patch("app.audio_uploads_collection", None):
            data = {"audio": (io.BytesIO(b"abc"), "ok.wav")}
            resp = client.post("/upload", data=data)
            assert resp.status_code == 503
            assert "database connection not available" in resp.get_json().get(
                "error", ""
            )


# ----------------------------------------------------------------------
# /api/stats TESTS
# ----------------------------------------------------------------------
class TestStatsRoute:
    @patch("app.audio_uploads_collection")
    def test_stats_returns_counts(self, mock_coll, client):
        mock_coll.count_documents = MagicMock(return_value=5)
        ml_results_cache.extend([{"a": 1}, {"b": 2}])

        response = client.get("/api/stats")
        data = response.get_json()

        assert response.status_code == 200
        assert data["total_uploads"] == 5
        assert data["total_analyses"] == 2

    def test_stats_fails_without_db(self, client):
        # Force DB connection missing
        with patch("app.audio_uploads_collection", None):
            response = client.get("/api/stats")
            assert response.status_code == 503

    @patch("app.audio_uploads_collection")
    def test_stats_handles_exception_and_returns_500(self, mock_coll, client):
        def raise_exc(_):
            raise RuntimeError("boom")

        mock_coll.count_documents = MagicMock(side_effect=raise_exc)
        response = client.get("/api/stats")
        assert response.status_code == 500
        assert "Failed to get stats" in response.get_json().get("error", "")


# ----------------------------------------------------------------------
# /api/ml-result & /api/ml-results & /api/languages TESTS
# ----------------------------------------------------------------------
class TestMLResultRoutes:
    def test_ml_result_post_success(self, client):
        payload = {
            "language": "english",
            "transcript": "hello",
            "audio_path": "/tmp/a.wav",
        }
        response = client.post("/api/ml-result", json=payload)
        data = response.get_json()

        assert response.status_code == 200
        assert data["result"]["language"] == "english"
        assert len(ml_results_cache) == 1

    def test_ml_result_missing_data(self, client):
        # send no JSON and no content-type -> app uses get_json(silent=True) and returns 400
        response = client.post("/api/ml-result", data={})
        assert response.status_code == 400
        assert response.get_json()["error"] == "No data provided"

    def test_get_ml_results_limit_param_invalid_returns_500(self, client):
        # invalid int conversion should raise and the endpoint returns 500
        r = client.get("/api/ml-results?limit=notanint")
        assert r.status_code == 500
        assert "Failed to get results" in r.get_json()["error"]

    def test_get_ml_results_returns_subset(self, client):
        ml_results_cache.append({"language": "spanish"})
        ml_results_cache.append({"language": "english"})
        r = client.get("/api/ml-results?limit=1")
        assert r.status_code == 200
        assert len(r.get_json()["results"]) == 1

    def test_language_distribution(self, client):
        ml_results_cache.extend(
            [
                {"language": "english"},
                {"language": "english"},
                {"language": "spanish"},
            ]
        )

        response = client.get("/api/languages")
        data = response.get_json()

        assert response.status_code == 200
        langs = data["languages"]
        assert langs[0]["language"] == "english"
        assert langs[0]["count"] == 2
        assert langs[1]["language"] == "spanish"

    def test_language_distribution_endpoint_error_returns_500(self, client):
        # Patch the cache to None to cause a TypeError inside the endpoint
        with patch("app.ml_results_cache", None):
            r = client.get("/api/languages")
            assert r.status_code == 500
            assert "Failed to get language distribution" in r.get_json()["error"]


# ----------------------------------------------------------------------
# /api/uploads
# ----------------------------------------------------------------------
class TestUploadsRoute:
    @patch("app.audio_uploads_collection")
    def test_get_uploads_basic(self, mock_coll, client):
        # Provide a datetime so isoformat path is used
        now = datetime.utcnow()
        mock_coll.find.return_value.sort.return_value.limit.return_value = [
            {"_id": 123, "upload_date": now, "file_id": 456}
        ]

        response = client.get("/api/uploads")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        uploads = data["uploads"]
        assert uploads[0]["upload_date"] == now.isoformat()
        assert isinstance(uploads[0]["_id"], str)
        assert isinstance(uploads[0]["file_id"], str)

    def test_uploads_no_db(self, client):
        with patch("app.audio_uploads_collection", None):
            r = client.get("/api/uploads")
            assert r.status_code == 503

    @patch("app.audio_uploads_collection")
    def test_get_uploads_handles_exception_and_returns_500(self, mock_coll, client):
        def bad_find(*_a, **_k):
            raise RuntimeError("fail")

        mock_coll.find = MagicMock(side_effect=bad_find)
        r = client.get("/api/uploads")
        assert r.status_code == 500
        assert "Failed to get uploads" in r.get_json()["error"]


# ----------------------------------------------------------------------
# /api/analyses
# ----------------------------------------------------------------------
class TestAnalysesRoute:
    @patch("app.analyses_collection")
    def test_get_analyses(self, mock_coll, client):
        now = datetime.utcnow()
        mock_coll.find.return_value.sort.return_value.limit.return_value = [
            {"_id": 999, "analysis_date": now, "file_id": "abc"}
        ]

        response = client.get("/api/analyses")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        analyses = data["analyses"]
        assert analyses[0]["analysis_date"] == now.isoformat()
        assert isinstance(analyses[0]["_id"], str)
        assert isinstance(analyses[0]["file_id"], str)

    def test_analyses_no_db(self, client):
        with patch("app.analyses_collection", None):
            r = client.get("/api/analyses")
            assert r.status_code == 503

    @patch("app.analyses_collection")
    def test_get_analyses_handles_exception_and_returns_500(self, mock_coll, client):
        def bad_find(*_a, **_k):
            raise RuntimeError("boom")

        mock_coll.find = MagicMock(side_effect=bad_find)
        r = client.get("/api/analyses")
        assert r.status_code == 500
        assert "Failed to get analyses" in r.get_json()["error"]
