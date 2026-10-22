"""Runs an interview: picks important code, asks about it, grades answers, and follows up."""
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from app.services.chunker import Chunk
from app.services.code_index import CodeIndex
from app.services import llm

MAX_TOPICS = 4          # how many pieces of code the interview covers
MAX_FOLLOW_UPS = 2      # extra questions allowed on the same topic
RELATED_CHARS = 800     # max characters of each related chunk sent to the LLM

SYSTEM_PROMPT = """You are a senior software engineer interviewing a student about a project they say they built.
Ask about THEIR actual code: design choices, how it works, what could go wrong, and how they would improve it.
Ask exactly ONE question at a time, in at most two short sentences, like a real interviewer speaking.
Mention the function or file you are asking about. Never give away the answer inside the question."""


@dataclass
class Turn:
    topic: str       # e.g. "clone_repo in services/repo_fetcher.py"
    question: str
    answer: str = ""
    score: int | None = None   # 0-10, filled in after the answer is graded
    got_right: str = ""
    missed: str = ""


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


def parse_score(value) -> int:
    """The LLM might send 7, "7", 7.5 or "7/10". Turn any of these into a whole number from 0 to 10."""
    try:
        number = float(str(value).split("/")[0].strip())
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, round(number)))


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
    # Keep related code short: it's extra context, and the free LLM plan limits tokens per minute
    related_text = "\n\n".join(f"{describe(c)}:\n```\n{c.content[:RELATED_CHARS]}\n```" for c in related)

    # One LLM call both grades the answer and decides whether to follow up
    history = "\n".join(f"Q: {t.question}\nA: {t.answer}" for t in interview.turns if t.topic == turn.topic)
    can_follow_up = interview.follow_ups < MAX_FOLLOW_UPS
    prompt = (
        f"Code for {describe(chunk)}:\n```\n{chunk.content}\n```\n\n"
        f"Related code from the same project:\n{related_text or '(none)'}\n\n"
        f"Conversation so far on this topic:\n{history}\n\n"
        "Grade ONLY the latest answer against the actual code above.\n"
        "Reply in JSON with these keys:\n"
        '  "score": 0-10 (0 = no answer or wrong, 5 = partly right, 10 = complete and precise),\n'
        '  "got_right": one short sentence on what was correct ("" if nothing),\n'
        '  "missed": one short sentence on what was wrong or missing ("" if nothing). '
        "If the answer talks about different code than the question asked about, say so here,\n"
        '  "follow_up": true or false,\n'
        '  "question": the follow-up question if follow_up is true, otherwise "".\n'
        + ("Set follow_up to true if the answer was vague, partly wrong, or worth digging into."
           if can_follow_up else "Set follow_up to false: this topic is finished.")
    )
    result = llm.chat(SYSTEM_PROMPT, prompt, as_json=True)
    if not isinstance(result, dict):
        result = {}
    turn.score = parse_score(result.get("score"))
    turn.got_right = str(result.get("got_right") or "")
    turn.missed = str(result.get("missed") or "")

    if can_follow_up and result.get("follow_up") and result.get("question"):
        interview.follow_ups += 1
        interview.turns.append(Turn(turn.topic, result["question"]))
        return result["question"]

    # Move on to the next topic
    interview.topic_number += 1
    interview.follow_ups = 0
    if interview.topic_number >= len(interview.topics):
        interview.done = True
        return None
    return ask_first_question(interview)


def build_scorecard(interview: Interview) -> dict:
    """Average the scores per topic and ask the LLM for a short study plan."""
    graded = [t for t in interview.turns if t.score is not None]
    by_topic = defaultdict(list)
    for t in graded:
        by_topic[t.topic].append(t)

    topics = []
    for topic, turns in by_topic.items():
        avg = sum(t.score for t in turns) / len(turns)
        topics.append({
            "topic": topic,
            "score": round(avg, 1),
            "feedback": [{"question": t.question, "score": t.score, "got_right": t.got_right, "missed": t.missed}
                         for t in turns],
        })
    topics.sort(key=lambda t: t["score"])  # weakest first

    overall = round(sum(t.score for t in graded) / len(graded), 1) if graded else 0

    summary = ""
    if graded:
        notes = "\n".join(f"- {t['topic']}: {t['score']}/10. Missed: "
                          + "; ".join(f["missed"] for f in t["feedback"] if f["missed"]) for t in topics)
        summary = llm.chat(
            "You are a friendly interview coach for a student preparing for placements.",
            f"Interview results (score out of 10 per topic):\n{notes}\n\n"
            "In 3 short bullet points, tell the student what to study or revise in their own code before "
            "a real interview. Be specific and encouraging. Plain text, no headings.",
        )

    return {
        "overall_score": overall,
        "strong_areas": [t["topic"] for t in topics if t["score"] >= 7],
        "weak_areas": [t["topic"] for t in topics if t["score"] < 5],
        "topics": topics,
        "study_plan": summary,
    }
