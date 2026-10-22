import numpy as np
import pytest

from app.services import interviewer
from app.services.chunker import Chunk
from app.services.interviewer import build_scorecard, parse_score, pick_topics, start_interview, submit_answer


def make_chunk(file, name, length, kind="function"):
    return Chunk(file, "Python", kind, name, 1, length, f"def {name}():\n    pass")


class FakeIndex:
    """Stands in for CodeIndex so tests don't need the embedding model."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.vectors = np.zeros((len(chunks), 3))

    def search(self, query, top_k=5):
        return []


class FakeLLM:
    """Returns scripted replies and remembers what it was asked."""

    def __init__(self, follow_up_every_time=False, score=6):
        self.follow_up = follow_up_every_time
        self.score = score
        self.calls = 0

    def chat(self, system, user, as_json=False):
        self.calls += 1
        if as_json:
            return {"score": self.score, "got_right": "good", "missed": "", "follow_up": self.follow_up,
                    "question": f"follow-up {self.calls}?"}
        return f"question {self.calls}?"


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(interviewer.llm, "chat", llm.chat)
    return llm


@pytest.mark.parametrize("value, expected", [
    (7, 7), ("7", 7), ("7/10", 7), (7.6, 8), (None, 0), ("abc", 0), (15, 10), (-3, 0),
])
def test_parse_score_handles_messy_values(value, expected):
    assert parse_score(value) == expected


def test_pick_topics_takes_biggest_chunk_per_file():
    chunks = [
        make_chunk("a.py", "small_a", 5),
        make_chunk("a.py", "big_a", 50),
        make_chunk("b.py", "only_b", 10),
        make_chunk("c.py", "", 30, kind="module"),  # module chunks are never topics
    ]
    names = [c.name for c in pick_topics(chunks)]
    assert names == ["big_a", "only_b"]


def test_pick_topics_respects_max(monkeypatch):
    monkeypatch.setattr(interviewer, "MAX_TOPICS", 2)
    chunks = [make_chunk(f"f{i}.py", f"fn{i}", i + 1) for i in range(5)]
    assert len(pick_topics(chunks)) == 2


def test_interview_without_follow_ups_visits_every_topic_once(fake_llm):
    index = FakeIndex([make_chunk("a.py", "one", 10), make_chunk("b.py", "two", 5)])
    interview = start_interview(index)

    assert submit_answer(interview, "answer 1") is not None  # moves to topic 2
    assert submit_answer(interview, "answer 2") is None       # interview over
    assert interview.done
    assert [t.score for t in interview.turns] == [6, 6]


def test_follow_ups_are_capped_per_topic(fake_llm):
    fake_llm.follow_up = True
    index = FakeIndex([make_chunk("a.py", "one", 10)])
    interview = start_interview(index)

    answers = 0
    while not interview.done:
        submit_answer(interview, "vague")
        answers += 1
    # 1 first question + MAX_FOLLOW_UPS follow-ups on the only topic
    assert answers == 1 + interviewer.MAX_FOLLOW_UPS


def test_scorecard_sorts_weakest_first(monkeypatch):
    index = FakeIndex([make_chunk("a.py", "strong", 10), make_chunk("b.py", "weak", 5)])
    scores = iter([9, 2])

    def chat(system, user, as_json=False):
        if as_json:
            return {"score": next(scores), "follow_up": False}
        return "study plan" if "coach" in system else "question?"

    monkeypatch.setattr(interviewer.llm, "chat", chat)
    interview = start_interview(index)
    submit_answer(interview, "great answer")
    submit_answer(interview, "bad answer")

    card = build_scorecard(interview)
    assert card["overall_score"] == 5.5
    assert [t["topic"] for t in card["topics"]] == ["function `weak` in b.py", "function `strong` in a.py"]
    assert card["weak_areas"] == ["function `weak` in b.py"]
    assert card["strong_areas"] == ["function `strong` in a.py"]
    assert card["study_plan"] == "study plan"
