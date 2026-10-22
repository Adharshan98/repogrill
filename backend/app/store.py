"""Saves and loads repos and interviews, converting between database rows and the objects the app uses."""
import uuid
from datetime import timezone

import numpy as np

from app.db import ChunkRow, InterviewRow, RepoRow, SessionLocal, TurnRow
from app.services.chunker import Chunk
from app.services.code_index import CodeIndex
from app.services.interviewer import Interview, Turn

# Rebuilding an index means reading every chunk from disk, so keep recently used ones in memory
_index_cache: dict[str, CodeIndex] = {}


def save_repo(url: str, index: CodeIndex) -> str:
    repo_id = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        repo = RepoRow(id=repo_id, url=url)
        for position, (chunk, vector) in enumerate(zip(index.chunks, index.vectors)):
            repo.chunks.append(ChunkRow(
                position=position, file=chunk.file, language=chunk.language, kind=chunk.kind, name=chunk.name,
                start_line=chunk.start_line, end_line=chunk.end_line, content=chunk.content,
                embedding=np.asarray(vector, dtype=np.float32).tobytes(),
            ))
        db.add(repo)
        db.commit()
    _index_cache[repo_id] = index
    return repo_id


def load_index(repo_id: str) -> CodeIndex | None:
    if repo_id in _index_cache:
        return _index_cache[repo_id]
    with SessionLocal() as db:
        repo = db.get(RepoRow, repo_id)
        if repo is None:
            return None
        chunks = [Chunk(r.file, r.language, r.kind, r.name, r.start_line, r.end_line, r.content) for r in repo.chunks]
        vectors = np.array([np.frombuffer(r.embedding, dtype=np.float32) for r in repo.chunks]).reshape(-1, 384)
    index = CodeIndex(chunks, vectors)
    _index_cache[repo_id] = index
    return index


def save_interview(interview: Interview) -> None:
    """Insert or update the interview and all its turns."""
    positions = [next(i for i, c in enumerate(interview.index.chunks) if c is topic) for topic in interview.topics]
    with SessionLocal() as db:
        row = db.get(InterviewRow, interview.id) or InterviewRow(id=interview.id, repo_id=interview.repo_id)
        row.topic_positions = positions
        row.topic_number = interview.topic_number
        row.follow_ups = interview.follow_ups
        row.done = interview.done
        row.turns = [
            TurnRow(position=i, topic=t.topic, question=t.question, answer=t.answer, score=t.score,
                    got_right=t.got_right, missed=t.missed)
            for i, t in enumerate(interview.turns)
        ]
        db.add(row)
        db.commit()


def load_interview(interview_id: str) -> Interview | None:
    with SessionLocal() as db:
        row = db.get(InterviewRow, interview_id)
        if row is None:
            return None
        turns = [Turn(t.topic, t.question, t.answer, t.score, t.got_right, t.missed) for t in row.turns]
        repo_id, positions = row.repo_id, row.topic_positions
        state = (row.topic_number, row.follow_ups, row.done)

    index = load_index(repo_id)
    interview = Interview(interview_id, index, [index.chunks[p] for p in positions], turns, *state)
    interview.repo_id = repo_id
    return interview


def get_repo_url(repo_id: str) -> str:
    with SessionLocal() as db:
        repo = db.get(RepoRow, repo_id)
        return repo.url if repo else ""


def get_study_plan(interview_id: str) -> str | None:
    with SessionLocal() as db:
        row = db.get(InterviewRow, interview_id)
        return row.study_plan if row else None


def save_study_plan(interview_id: str, plan: str) -> None:
    with SessionLocal() as db:
        row = db.get(InterviewRow, interview_id)
        row.study_plan = plan
        db.commit()


def list_interviews() -> list[dict]:
    """Past interviews, newest first, with their average score."""
    with SessionLocal() as db:
        rows = db.query(InterviewRow).order_by(InterviewRow.created_at.desc()).all()
        result = []
        for row in rows:
            scores = [t.score for t in row.turns if t.score is not None]
            result.append({
                "interview_id": row.id,
                "repo_url": row.repo.url,
                # SQLite drops the timezone; we always store UTC, so put it back
                "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat(),
                "done": row.done,
                "questions_answered": len(scores),
                "average_score": round(sum(scores) / len(scores), 1) if scores else None,
            })
    return result
