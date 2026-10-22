from pathlib import Path

from app.services.chunker import CHUNK_LINES, chunk_file, chunk_repo

PYTHON_SOURCE = '''import os

LIMIT = 5


@decorator
def first(a):
    return a + 1


class Thing:
    def method(self):
        return 2


async def second():
    pass
'''


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_python_split_by_function_and_class(tmp_path):
    path = write(tmp_path, "app.py", PYTHON_SOURCE)
    chunks = chunk_file(path, tmp_path)

    by_name = {c.name: c for c in chunks if c.name}
    assert set(by_name) == {"first", "Thing", "second"}
    assert by_name["Thing"].kind == "class"
    assert by_name["second"].kind == "function"
    # The decorator line belongs to the function it decorates
    assert by_name["first"].content.startswith("@decorator")


def test_leftover_code_goes_into_module_chunk(tmp_path):
    path = write(tmp_path, "app.py", PYTHON_SOURCE)
    module = [c for c in chunk_file(path, tmp_path) if c.kind == "module"]

    assert len(module) == 1
    assert "import os" in module[0].content
    assert "LIMIT = 5" in module[0].content
    assert "def first" not in module[0].content


def test_broken_python_falls_back_to_line_chunks(tmp_path):
    path = write(tmp_path, "broken.py", "def oops(:\n    pass\n")
    chunks = chunk_file(path, tmp_path)

    assert [c.kind for c in chunks] == ["lines"]


def test_other_languages_use_line_chunks(tmp_path):
    source = "\n".join(f"console.log({i});" for i in range(CHUNK_LINES + 10))
    path = write(tmp_path, "app.js", source)
    chunks = chunk_file(path, tmp_path)

    assert len(chunks) == 2
    assert chunks[0].language == "JavaScript"
    assert (chunks[0].start_line, chunks[0].end_line) == (1, CHUNK_LINES)


def test_skips_dependency_folders_and_unknown_files(tmp_path):
    write(tmp_path, "src/main.py", "def run():\n    pass\n")
    write(tmp_path, "node_modules/lib/index.js", "console.log(1)")
    write(tmp_path, ".venv/lib/site.py", "def x():\n    pass\n")
    write(tmp_path, "notes.txt", "hello")

    files = {c.file for c in chunk_repo(tmp_path)}
    assert files == {"src/main.py"}
