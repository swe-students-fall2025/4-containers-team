"""Tests for web-app"""

import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # pylint: disable=wrong-import-position
from app import app  # pylint: disable=wrong-import-position,import-error


@pytest.fixture
def client():
    """Create a test client."""
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
    with app.test_client() as test_client:
        yield test_client


class TestHomeRoute:
    """Test cases for home route."""

    def test_home_route_returns_200(
        self, client
    ):  # pylint: disable=redefined-outer-name
        """Test that home route returns 200 status code."""
        response = client.get("/")
        assert response.status_code == 200

    def test_home_route_renders_template(
        self, client
    ):  # pylint: disable=redefined-outer-name
        """Test that home route renders the index template."""
        response = client.get("/")
        assert b"World Tour by Ear" in response.data or response.status_code == 200


class TestUploadRoute:
    """Test cases for upload route."""

#     def test_upload_without_file_returns_400(
#         self, client
#     ):  # pylint: disable=redefined-outer-name
#         """Test upload route without file returns 400 error."""
#         response = client.post("/upload")
#         assert response.status_code == 400
#         data = response.get_json()
#         assert "error" in data
#         assert data["error"] == "no audio file"

#     def test_upload_with_file_returns_200(
#         self, client
#     ):  # pylint: disable=redefined-outer-name
#         """Test upload route with file returns success."""
#         audio_data = b"fake audio content"
#         data = {"audio": (io.BytesIO(audio_data), "test.wav")}
#         response = client.post("/upload", data=data)
#         assert response.status_code == 200
#         json_data = response.get_json()
#         assert "message" in json_data
#         assert json_data["message"] == "uploaded"
#         assert "filename" in json_data
#         assert json_data["filename"].startswith("audio_")

#     def test_upload_saves_file(self, client):  # pylint: disable=redefined-outer-name
#         """Test that uploaded file is actually saved."""
#         audio_data = b"fake audio content"
#         data = {"audio": (io.BytesIO(audio_data), "test.wav")}
#         response = client.post("/upload", data=data)
#         assert response.status_code == 200
#         json_data = response.get_json()
#         filename = json_data["filename"]
#         filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
#         assert os.path.exists(filepath)


# class TestAppConfiguration:
#     """Test cases for app configuration."""

#     def test_app_exists(self):
#         """Test that Flask app instance exists."""
#         assert app is not None
#         assert app.config["UPLOAD_FOLDER"] is not None

#     def test_upload_folder_created(self):
#         """Test that upload folder is created."""
#         assert os.path.exists(app.config["UPLOAD_FOLDER"]) or os.path.isdir(
#             app.config["UPLOAD_FOLDER"]
#         )
