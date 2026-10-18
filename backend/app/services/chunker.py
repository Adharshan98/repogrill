"""Walks a repository and splits its source files into chunks the AI can read.

Why chunks? LLMs have a limited context window, so we can't send a whole repo at
once. Later we'll embed each chunk and retrieve only the relevant ones (RAG).
"""
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
    start_line: int
    end_line: int
    content: str


def iter_source_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in LANGUAGES and path.stat().st_size <= MAX_FILE_BYTES:
            yield path


def chunk_file(path: Path, root: Path) -> list[Chunk]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    rel = path.relative_to(root).as_posix()
    lang = LANGUAGES[path.suffix.lower()]
    chunks = []
    for start in range(0, len(lines), CHUNK_LINES):
        part = lines[start:start + CHUNK_LINES]
        if any(line.strip() for line in part):
            chunks.append(Chunk(rel, lang, start + 1, start + len(part), "\n".join(part)))
    return chunks


def chunk_repo(root: Path) -> list[Chunk]:
    chunks = []
    for path in iter_source_files(root):
        chunks.extend(chunk_file(path, root))
    return chunks
