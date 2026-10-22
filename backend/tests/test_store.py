import numpy as np

from app import store
from app.services import interviewer
from app.services.chunker import Chunk
from app.services.code_index import CodeIndex
from app.services.interviewer import start_interview, submit_answer


def make_index():
    chunks = [
        Chunk("a.py", "Python", "function", "alpha", 1, 20, "def alpha():\n    pass"),
        Chunk("b.py", "Python", "class", "Beta", 1, 10, "class Beta:\n    pass"),
    ]
    vectors = np.random.default_rng(0).random((2, 384), dtype=np.float32)
    return CodeIndex(chunks, vectors)


def fake_chat(system, user, as_json=False):
    if as_json:
        return {"score": 7, "got_right": "yes", "missed": "no", "follow_up": False}
    return "What does this do?"


def test_repo_survives_restart():
    index = make_index()
    repo_id = store.save_repo("https://github.com/x/y", index)

    store._index_cache.clear()  # simulate a server restart
    loaded = store.load_index(repo_id)

    assert [c.name for c in loaded.chunks] == ["alpha", "Beta"]
    assert np.allclose(loaded.vectors, index.vectors)


def test_interview_survives_restart(monkeypatch):
    monkeypatch.setattr(interviewer.llm, "chat", fake_chat)
    repo_id = store.save_repo("https://github.com/x/y", make_index())
    interview = start_interview(store.load_index(repo_id))
    interview.repo_id = repo_id
    submit_answer(interview, "It returns nothing.")
    store.save_interview(interview)

    store._index_cache.clear()
    loaded = store.load_interview(interview.id)

    assert loaded.topic_number == 1
    assert [t.answer for t in loaded.turns] == ["It returns nothing.", ""]
    assert loaded.turns[0].score == 7
    assert [c.name for c in loaded.topics] == ["alpha", "Beta"]

    # The loaded interview can carry on where it stopped
    assert submit_answer(loaded, "It's a class.") is None
    assert loaded.done


def test_unknown_ids_return_none():
    assert store.load_index("missing") is None
    assert store.load_interview("missing") is None


def test_list_interviews_shows_average(monkeypatch):
    monkeypatch.setattr(interviewer.llm, "chat", fake_chat)
    repo_id = store.save_repo("https://github.com/x/listed", make_index())
    interview = start_interview(store.load_index(repo_id))
    interview.repo_id = repo_id
    submit_answer(interview, "answer")
    store.save_interview(interview)

    entry = next(i for i in store.list_interviews() if i["interview_id"] == interview.id)
    assert entry["repo_url"] == "https://github.com/x/listed"
    assert entry["average_score"] == 7
    assert entry["done"] is False
