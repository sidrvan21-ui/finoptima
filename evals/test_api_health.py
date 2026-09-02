from fastapi.testclient import TestClient

from api.main import app


def test_health():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is True
    assert body.get("money_db") in ("postgres", "sqlite")
    assert isinstance(body.get("llm_providers"), list)


def test_website_home():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert b"Run audit" in res.content
