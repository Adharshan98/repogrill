"""Walks a repository and splits its source files into chunks the AI can read.

Why chunks? LLMs have a limited context window, so we can't send a whole repo at
once. Later we'll embed each chunk and retrieve only the relevant ones (RAG).

Python files are split by function and class using the `ast` module, so a function
is never cut in half. Other languages fall back to fixed-size line chunks for now.
"""
import ast
from dataclasses import dataclass
from pathlib import Path

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
    ".c": "C", ".cpp": "C++", ".cs": "C#", ".kt": "Kotlin", ".rs": "Rust",
    ".sql": "SQL", ".html": "HTML", ".css": "CSS",
}

# Folders that contain generated or third-party code, not the user's own work
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".next", "target"}

CHUNK_LINES = 60       # lines per chunk
MAX_FILE_BYTES = 200_000  # skip huge files (usually generated/minified)


@dataclass
class Chunk:
    file: str
    language: str
    kind: str        # "function", "class", "module" (top-level code) or "lines"
    name: str        # function/class name, or "" when there isn't one
    start_line: int
    end_line: int
    content: str


def iter_source_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in LANGUAGES and path.stat().st_size <= MAX_FILE_BYTES:
            yield path


def chunk_by_lines(lines: list[str], rel: str, lang: str) -> list[Chunk]:
    chunks = []
    for start in range(0, len(lines), CHUNK_LINES):
        part = lines[start:start + CHUNK_LINES]
        if any(line.strip() for line in part):
            chunks.append(Chunk(rel, lang, "lines", "", start + 1, start + len(part), "\n".join(part)))
    return chunks


def chunk_python(source: str, lines: list[str], rel: str) -> list[Chunk]:
    """One chunk per top-level function or class; leftover code becomes one "module" chunk."""
    tree = ast.parse(source)
    chunks = []
    used = set()  # line numbers already inside a function/class chunk

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Include decorators like @app.get(...) that sit above the definition
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            end = node.end_lineno
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            chunks.append(Chunk(rel, "Python", kind, node.name, start, end, "\n".join(lines[start - 1:end])))
            used.update(range(start, end + 1))

    # Imports, constants, etc. that aren't inside any function or class
    rest = [line for i, line in enumerate(lines, start=1) if i not in used]
    if any(line.strip() for line in rest):
        chunks.insert(0, Chunk(rel, "Python", "module", "", 1, len(lines), "\n".join(rest).strip()))
    return chunks


def chunk_file(path: Path, root: Path) -> list[Chunk]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    lines = source.splitlines()
    rel = path.relative_to(root).as_posix()
    lang = LANGUAGES[path.suffix.lower()]

    if lang == "Python":
        try:
            return chunk_python(source, lines, rel)
        except SyntaxError:
            pass  # broken or Python 2 file: fall back to line chunks
    return chunk_by_lines(lines, rel, lang)


def chunk_repo(root: Path) -> list[Chunk]:
    chunks = []
    for path in iter_source_files(root):
        chunks.extend(chunk_file(path, root))
    return chunks
