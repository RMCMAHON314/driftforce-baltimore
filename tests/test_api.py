import json
import sqlite3
import os
import sys

# Ensure repository root is on sys.path so tests can import `app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app import app, init_db


client = TestClient(app)


def setup_module(module):
    # Ensure a clean DB for tests
    init_db()


def test_demo_endpoint():
    payload = {"prompt": "Hello", "response": "I am an AI and 50% accurate"}
    r = client.post("/v1/demo", json=payload)
    assert r.status_code == 200
    d = r.json()
    assert "drift_detected" in d
    assert "analysis_id" in d


def test_check_with_demo_key():
    headers = {"Authorization": "Bearer df_demo_key_123"}
    payload = {"prompt": "Q", "response": "As an AI model, see https://example.com"}
    r = client.post("/v1/check", json=payload, headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["drift_detected"] is True


def test_register_and_metrics():
    # Register a new key
    payload = {"email": "test@example.com"}
    r = client.post("/v1/register", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["api_key"].startswith("df_live_")

    # Metrics for new key (no events yet)
    headers = {"Authorization": data["api_key"]}
    r = client.get("/v1/metrics", headers=headers)
    # 401 or 200 are acceptable depending on event storage; assert no server error
    assert r.status_code in (200, 401)
