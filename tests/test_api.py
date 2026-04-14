from fastapi.testclient import TestClient
from app.main_test import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"


def test_predict_validation():
    payload = {
        "patent_id": "RU-TEST",
        "ai_ipc": (
            "AI_IPC:A61K31/00 (20.03%);"
            "A61K31/497 (5.22%);"
            "A61P35/00 (13.87%);"
        ),
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    