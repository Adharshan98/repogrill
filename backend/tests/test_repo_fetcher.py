import pytest

from app.services.repo_fetcher import GITHUB_URL, RepoFetchError, clone_repo


@pytest.mark.parametrize("url", [
    "https://github.com/owner/repo",
    "https://github.com/owner/repo.git",
    "https://github.com/my-org/my.repo/",
])
def test_accepts_github_urls(url):
    assert GITHUB_URL.match(url)


@pytest.mark.parametrize("url", [
    "https://evil.com/owner/repo",
    "http://github.com/owner/repo",
    "https://github.com/owner",
    "https://github.com/owner/repo; rm -rf /",
    "file:///etc/passwd",
])
def test_rejects_other_urls(url):
    assert not GITHUB_URL.match(url)
    with pytest.raises(RepoFetchError):
        clone_repo(url)
