from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_variant_format_colon():
    # This should NOT return 400. It might return 404 if not found in ES, or 500 if ES is down,
    # but 400 means validation failed.
    response = client.get("/variant/17:43071077-T-C")
    assert response.status_code != 400

def test_variant_format_hyphen():
    # Standard format should still work
    response = client.get("/variant/17-43071077-T-C")
    assert response.status_code != 400

def test_variant_format_invalid():
    # Invalid format should return 400
    response = client.get("/variant/invalid-format")
    assert response.status_code == 400
