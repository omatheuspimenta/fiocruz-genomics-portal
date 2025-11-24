"""
Basic tests for the FastAPI application.
TODO: Expand with more comprehensive tests.
"""
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_read_main():
    response = client.get("/stats")
    assert response.status_code == 200
    assert "total_variants" in response.json()

def test_variant_validation():
    response = client.get("/variant/invalid-id")
    assert response.status_code == 400
