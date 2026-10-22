"""Runs an interview: picks important code, asks about it, and follows up on answers."""
import uuid
from dataclasses import dataclass, field

from app.services.chunker import Chunk
from app.services.code_index import CodeIndex
from app.services import llm

MAX_TOPICS = 4          # how many pieces of code the interview covers
MAX_FOLLOW_UPS = 2      # extra questions allowed on the same topic

SYSTEM_PROMPT = """You are a senior software engineer interviewing a student about a project they say they built.
Ask about THEIR actual code: design choices, how it works, what could go wrong, and how they would improve it.
Ask one clear, specific question at a time. Mention the function or file you are asking about.
Never give away the answer inside the question."""


@dataclass
class Turn:
    topic: str       # e.g. "clone_repo in services/repo_fetcher.py"
    question: str
    answer: str = ""


@dataclass
class Interview:
    id: str
    index: CodeIndex
    topics: list[Chunk]
    turns: list[Turn] = field(default_factory=list)
    topic_number: int = 0
    follow_ups: int = 0
    done: bool = False


def pick_topics(chunks: list[Chunk]) -> list[Chunk]:
    """Choose the biggest functions/classes, at most one per file, so the interview covers different areas."""
    candidates = [c for c in chunks if c.kind in ("function", "class", "lines")]
    candidates.sort(key=lambda c: c.end_line - c.start_line, reverse=True)
    picked, seen_files = [], set()
    for chunk in candidates:
        if chunk.file not in seen_files:
            picked.append(chunk)
            seen_files.add(chunk.file)
        if len(picked) == MAX_TOPICS:
            break
    return picked


def describe(chunk: Chunk) -> str:
    label = f"{chunk.kind} `{chunk.name}`" if chunk.name else f"lines {chunk.start_line}-{chunk.end_line}"
    return f"{label} in {chunk.file}"


def project_overview(index: CodeIndex) -> str:
    files = sorted({c.file for c in index.chunks})
    return "Project files:\n" + "\n".join(f"- {f}" for f in files)


def ask_first_question(interview: Interview) -> str:
    chunk = interview.topics[interview.topic_number]
    prompt = (
        f"{project_overview(interview.index)}\n\n"
        f"Code for {describe(chunk)}:\n```\n{chunk.content}\n```\n\n"
        "Ask your first interview question about this code."
    )
    question = llm.chat(SYSTEM_PROMPT, prompt)
    interview.turns.append(Turn(describe(chunk), question))
    return question


def start_interview(index: CodeIndex) -> Interview:
    topics = pick_topics(index.chunks)
    if not topics:
        raise ValueError("No code found to interview about.")
    interview = Interview(uuid.uuid4().hex[:8], index, topics)
    ask_first_question(interview)
    return interview


def submit_answer(interview: Interview, answer: str) -> str | None:
    """Record the answer, then return the next question, or None when the interview is over."""
    turn = interview.turns[-1]
    turn.answer = answer
    chunk = interview.topics[interview.topic_number]

    # RAG: fetch other code related to what the student said, so follow-ups can connect the dots
    related = [r.chunk for r in interview.index.search(answer, top_k=3) if r.chunk is not chunk][:2]
    related_text = "\n\n".join(f"{describe(c)}:\n```\n{c.content}\n```" for c in related)

    if interview.follow_ups < MAX_FOLLOW_UPS:
        history = "\n".join(f"Q: {t.question}\nA: {t.answer}" for t in interview.turns if t.topic == turn.topic)
        prompt = (
            f"Code for {describe(chunk)}:\n```\n{chunk.content}\n```\n\n"
            f"Related code from the same project:\n{related_text or '(none)'}\n\n"
            f"Conversation so far on this topic:\n{history}\n\n"
            'Reply in JSON: {"follow_up": true or false, "question": "..."}. '
            "Set follow_up to true if the answer was vague, wrong, or worth digging deeper into, "
            "and write that follow-up question. Otherwise set follow_up to false and leave question empty."
        )
        decision = llm.chat(SYSTEM_PROMPT, prompt, as_json=True)
        if decision.get("follow_up") and decision.get("question"):
            interview.follow_ups += 1
            interview.turns.append(Turn(turn.topic, decision["question"]))
            return decision["question"]

    # Move on to the next topic
    interview.topic_number += 1
    interview.follow_ups = 0
    if interview.topic_number >= len(interview.topics):
        interview.done = True
        return None
    return ask_first_question(interview)
