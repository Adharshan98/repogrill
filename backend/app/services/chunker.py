"""Walks a repository and splits its source files into chunks the AI can read.

Why chunks? LLMs have a limited context window, so we can't send a whole repo at
once. We embed each chunk and retrieve only the relevant ones (RAG).

Files are split by function and class so a function is never cut in half:
Python with the built-in `ast` module; JavaScript, TypeScript and Java with tree-sitter.
Other languages fall back to fixed-size line chunks.
"""
import ast
from dataclasses import dataclass
from pathlib import Path

from app.services import syntax_chunker

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
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


def python_spans(source: str) -> list[syntax_chunker.Span]:
    """Top-level functions and classes, including decorators like @app.get(...) above them."""
    spans = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            spans.append((start, node.end_lineno, kind, node.name))
    return spans


def chunks_from_spans(spans, lines: list[str], rel: str, lang: str) -> list[Chunk]:
    """One chunk per span; lines outside every span (imports, constants...) become one "module" chunk."""
    chunks = []
    used = set()
    for start, end, kind, name in spans:
        chunks.append(Chunk(rel, lang, kind, name, start, end, "\n".join(lines[start - 1:end])))
        used.update(range(start, end + 1))

    rest = [line for i, line in enumerate(lines, start=1) if i not in used]
    if any(line.strip() for line in rest):
        chunks.insert(0, Chunk(rel, lang, "module", "", 1, len(lines), "\n".join(rest).strip()))
    return chunks


def chunk_file(path: Path, root: Path) -> list[Chunk]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    lines = source.splitlines()
    rel = path.relative_to(root).as_posix()
    suffix = path.suffix.lower()
    lang = LANGUAGES[suffix]

    spans = []
    if lang == "Python":
        try:
            spans = python_spans(source)
        except SyntaxError:
            pass  # broken or Python 2 file: fall back to line chunks
    elif syntax_chunker.supports(suffix):
        spans = syntax_chunker.find_spans(source, suffix)

    if spans:
        return chunks_from_spans(spans, lines, rel, lang)
    return chunk_by_lines(lines, rel, lang)


def chunk_repo(root: Path) -> list[Chunk]:
    chunks = []
    for path in iter_source_files(root):
        chunks.extend(chunk_file(path, root))
    return chunks
