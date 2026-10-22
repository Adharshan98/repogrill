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


def test_analyze_rejects_repos_that_are_too_big_or_empty(monkeypatch, tmp_path):
    import app.main as main
    from app.services.chunker import Chunk

    monkeypatch.setattr(main, "clone_repo", lambda url: tmp_path)
    monkeypatch.setattr(main, "cleanup", lambda path: None)
    url = {"repo_url": "https://github.com/x/y"}

    monkeypatch.setattr(main, "chunk_repo", lambda path: [])
    assert client.post("/analyze", json=url).status_code == 400

    many = [Chunk("a.py", "Python", "function", f"f{i}", 1, 2, "pass") for i in range(main.MAX_CHUNKS + 1)]
    monkeypatch.setattr(main, "chunk_repo", lambda path: many)
    response = client.post("/analyze", json=url)
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
