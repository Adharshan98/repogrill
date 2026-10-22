from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_analyze_rejects_non_github_url():
    response = client.post("/analyze", json={"repo_url": "https://evil.com/x/y"})
    assert response.status_code == 400


def test_unknown_ids_return_404():
    assert client.get("/repos/nope/search", params={"q": "x"}).status_code == 404
    assert client.post("/repos/nope/interviews").status_code == 404
    assert client.post("/interviews/nope/answer", json={"answer": "x"}).status_code == 404
    assert client.get("/interviews/nope/scorecard").status_code == 404
