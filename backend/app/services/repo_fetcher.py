"""Downloads a public GitHub repository so we can analyze its code."""
import re
import shutil
import subprocess
import uuid
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2] / "workspace"

# Only allow plain public GitHub URLs like https://github.com/owner/repo
GITHUB_URL = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?$")


class RepoFetchError(Exception):
    pass


def clone_repo(repo_url: str) -> Path:
    """Shallow-clone the repo into a fresh folder and return its path."""
    if not GITHUB_URL.match(repo_url):
        raise RepoFetchError("Please provide a URL like https://github.com/owner/repo")

    target = WORKSPACE / uuid.uuid4().hex
    target.parent.mkdir(parents=True, exist_ok=True)

    # --depth 1 downloads only the latest commit, not the full history (much faster)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(target)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        raise RepoFetchError("Could not clone repo. Is it public and spelled correctly?")
    return target


def cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
