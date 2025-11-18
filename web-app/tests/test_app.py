import io
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Ensure app.py is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, ml_results_cache


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
        # HTML likely contains this text
        assert b"World Tour" in response.data or b"<html" in response.data


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


# ----------------------------------------------------------------------
# /api/ml-result & /api/ml-results & /api/languages TESTS
# ----------------------------------------------------------------------
class TestMLResultRoutes:
    def test_ml_result_post_success(self, client):
        payload = {"language": "english", "transcript": "hello", "audio_path": "/tmp/a.wav"}
        response = client.post("/api/ml-result", json=payload)
        data = response.get_json()

        assert response.status_code == 200
        assert data["result"]["language"] == "english"
        assert len(ml_results_cache) == 1

    def test_ml_result_missing_data(self, client):
        response = client.post("/api/ml-result", data={})
        assert response.status_code == 400

    def test_get_ml_results(self, client):
        ml_results_cache.append({"language": "spanish"})
        ml_results_cache.append({"language": "english"})

        response = client.get("/api/ml-results?limit=1")
        data = response.get_json()

        assert response.status_code == 200
        assert len(data["results"]) == 1

    def test_language_distribution(self, client):
        ml_results_cache.extend([
            {"language": "english"},
            {"language": "english"},
            {"language": "spanish"},
        ])

        response = client.get("/api/languages")
        data = response.get_json()

        assert response.status_code == 200
        langs = data["languages"]

        assert langs[0]["language"] == "english"
        assert langs[0]["count"] == 2
        assert langs[1]["language"] == "spanish"


# ----------------------------------------------------------------------
# /api/uploads
# ----------------------------------------------------------------------
class TestUploadsRoute:
    @patch("app.audio_uploads_collection")
    def test_get_uploads_basic(self, mock_coll, client):
        mock_coll.find.return_value.sort.return_value.limit.return_value = [
            {"_id": "1", "upload_date": None, "file_id": "a"}
        ]

        response = client.get("/api/uploads")
        assert response.status_code == 200
        data = response.get_json()

        assert data["total"] == 1

    def test_uploads_no_db(self, client):
        with patch("app.audio_uploads_collection", None):
            r = client.get("/api/uploads")
            assert r.status_code == 503


# ----------------------------------------------------------------------
# /api/analyses
# ----------------------------------------------------------------------
class TestAnalysesRoute:
    @patch("app.analyses_collection")
    def test_get_analyses(self, mock_coll, client):
        mock_coll.find.return_value.sort.return_value.limit.return_value = [
            {"_id": "1", "analysis_date": None, "file_id": "a"}
        ]

        response = client.get("/api/analyses")
        assert response.status_code == 200
        assert response.get_json()["total"] == 1

    def test_analyses_no_db(self, client):
        with patch("app.analyses_collection", None):
            r = client.get("/api/analyses")
            assert r.status_code == 503
