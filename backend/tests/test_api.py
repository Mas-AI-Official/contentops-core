"""
Basic API tests for Content Factory.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.main import app
from app.db import sync_engine


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    # Create tables
    SQLModel.metadata.create_all(sync_engine)
    
    with TestClient(app) as c:
        yield c


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Content Factory"
    assert data["status"] == "running"


def test_health(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_list_niches_empty(client):
    """Test listing niches when empty."""
    response = client.get("/api/niches/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_niche(client):
    """Test creating a niche."""
    niche_data = {
        "name": "test_niche",
        "description": "A test niche",
        "style": "narrator_broll",
        "posts_per_day": 1,
        "post_to_youtube": True,
        "post_to_instagram": True,
        "post_to_tiktok": False,
        "hashtags": ["test", "example"]
    }
    
    response = client.post("/api/niches/", json=niche_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "test_niche"
    assert data["id"] is not None


def test_get_settings(client):
    """Test getting settings."""
    response = client.get("/api/settings/")
    assert response.status_code == 200
    
    data = response.json()
    assert "ollama_base_url" in data
    assert "whisper_model" in data


def test_get_platform_status(client):
    """Test getting platform status."""
    response = client.get("/api/accounts/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "youtube" in data
    assert "instagram" in data
    assert "tiktok" in data


def test_list_jobs_empty(client):
    """Test listing jobs when empty."""
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_videos_empty(client):
    """Test listing videos when empty."""
    response = client.get("/api/videos/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
