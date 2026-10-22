import uuid
from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.chunker import chunk_repo
from app.services.code_index import CodeIndex
from app.services.repo_fetcher import RepoFetchError, cleanup, clone_repo

app = FastAPI(title="RepoGrill API")

# Analyzed repos, kept in memory for now (lost on restart; a database comes later)
REPOS: dict[str, CodeIndex] = {}


class AnalyzeRequest(BaseModel):
    repo_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        path = clone_repo(req.repo_url)
    except RepoFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        chunks = chunk_repo(path)
    finally:
        cleanup(path)

    repo_id = uuid.uuid4().hex[:8]
    REPOS[repo_id] = CodeIndex(chunks)

    files = sorted({c.file for c in chunks})
    return {
        "repo_id": repo_id,
        "repo_url": req.repo_url,
        "file_count": len(files),
        "chunk_count": len(chunks),
        "languages": Counter(c.language for c in chunks).most_common(),
        "chunk_kinds": Counter(c.kind for c in chunks).most_common(),
        "files": files,
    }


@app.get("/repos/{repo_id}/search")
def search(repo_id: str, q: str, top_k: int = 5):
    index = REPOS.get(repo_id)
    if index is None:
        raise HTTPException(status_code=404, detail="Repo not found. Analyze it first.")
    return [
        {
            "file": r.chunk.file,
            "kind": r.chunk.kind,
            "name": r.chunk.name,
            "lines": f"{r.chunk.start_line}-{r.chunk.end_line}",
            "score": round(r.score, 3),
        }
        for r in index.search(q, top_k)
    ]
