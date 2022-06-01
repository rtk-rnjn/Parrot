from __future__ import annotations

from fastapi.testclient import TestClient  # type: ignore

from ..api import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"success": True}