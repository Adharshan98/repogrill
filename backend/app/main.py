import uuid
from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.chunker import chunk_repo
from app.services.code_index import CodeIndex
from app.services.interviewer import Interview, describe, start_interview, submit_answer
from app.services.llm import LLMError
from app.services.repo_fetcher import RepoFetchError, cleanup, clone_repo

app = FastAPI(title="RepoGrill API")

# Analyzed repos and interviews, kept in memory for now (lost on restart; a database comes later)
REPOS: dict[str, CodeIndex] = {}
INTERVIEWS: dict[str, Interview] = {}


class AnalyzeRequest(BaseModel):
    repo_url: str


class AnswerRequest(BaseModel):
    answer: str


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


@app.post("/repos/{repo_id}/interviews")
def create_interview(repo_id: str):
    index = REPOS.get(repo_id)
    if index is None:
        raise HTTPException(status_code=404, detail="Repo not found. Analyze it first.")
    try:
        interview = start_interview(index)
    except (LLMError, ValueError) as e:
        raise HTTPException(status_code=502 if isinstance(e, LLMError) else 400, detail=str(e))
    INTERVIEWS[interview.id] = interview
    return {
        "interview_id": interview.id,
        "topics": [describe(c) for c in interview.topics],
        "question": interview.turns[-1].question,
    }


@app.post("/interviews/{interview_id}/answer")
def answer(interview_id: str, req: AnswerRequest):
    interview = INTERVIEWS.get(interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    if interview.done:
        raise HTTPException(status_code=400, detail="This interview is already finished.")
    try:
        next_question = submit_answer(interview, req.answer)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "done": interview.done,
        "topic": interview.turns[-1].topic,
        "question": next_question,
    }


@app.get("/interviews/{interview_id}")
def get_interview(interview_id: str):
    interview = INTERVIEWS.get(interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return {
        "done": interview.done,
        "turns": [{"topic": t.topic, "question": t.question, "answer": t.answer} for t in interview.turns],
    }
