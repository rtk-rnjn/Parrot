from __future__ import annotations

from fastapi.testclient import TestClient

from ..api import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    if response.status_code != 200:
        raise AssertionError
    if response.json() != {"success": True}:
        raise AssertionError
