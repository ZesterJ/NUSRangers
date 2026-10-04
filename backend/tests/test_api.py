"""Contract tests: response shapes must match src/api/types.ts in the app."""

from fastapi.testclient import TestClient

from app.main import app, parse_sms

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "provider": "echo"}


def test_chat_shape():
    r = client.post(
        "/chat",
        json={
            "packId": "agri",
            "locale": "sw",
            "systemPrompt": "You are ShambaMate",
            "messages": [{"role": "user", "content": "Nipande mahindi lini?"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"reply", "sources"}
    assert "Nipande mahindi lini?" in body["reply"]


def test_chat_rejects_empty_messages():
    r = client.post("/chat", json={"packId": "agri", "messages": []})
    assert r.status_code == 422


def test_analyze_shape_with_location_and_photo():
    r = client.post(
        "/analyze",
        json={
            "packId": "agri",
            "locale": "en",
            "fields": {"crop": "maize", "affected": 7, "location": {"lat": -1.29, "lng": 36.82}},
            "imageBase64": "aGVsbG8=",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"summary", "riskLevel", "actions"}
    assert body["riskLevel"] in {"low", "med", "high", None}
    assert isinstance(body["actions"], list)
    assert "with photo" in body["summary"]


def test_sms_webhook_returns_twiml():
    r = client.post("/sms/webhook", data={"Body": "HEALTH: child fever", "From": "+254700000000"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<Message>[echo:health] child fever</Message>" in r.text


def test_parse_sms_prefix_and_default():
    assert parse_sms("AGRI: when to plant?") == ("agri", "when to plant?")
    assert parse_sms("tourism:price") == ("tourism", "price")
    assert parse_sms("no prefix here") == ("agri", "no prefix here")
    assert parse_sms("Note: unknown prefix") == ("agri", "Note: unknown prefix")


def test_records_store_and_forward():
    r = client.post("/records", json={"id": "abc12345", "triage": {"level": "refer_now"}})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert client.post("/records", json={"triage": {}}).status_code == 422
