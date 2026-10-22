from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.chunker import chunk_repo
from app.services.repo_fetcher import RepoFetchError, cleanup, clone_repo

app = FastAPI(title="RepoGrill API")


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

    files = sorted({c.file for c in chunks})
    return {
        "repo_url": req.repo_url,
        "file_count": len(files),
        "chunk_count": len(chunks),
        "languages": Counter(c.language for c in chunks).most_common(),
        "chunk_kinds": Counter(c.kind for c in chunks).most_common(),
        "files": files,
        "sample_chunk": chunks[0].__dict__ if chunks else None,
    }
