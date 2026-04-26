"""Tests for devfolder.git module.

Tests for the new git wrappers (status, branches, stash_count,
last_commit_at) use real git fixture repos created with `git init` in
tmp_path. The legacy `get_git_remotes` parsing tests use subprocess
mocks, since they exercise URL-format edge cases that are easier to
construct as raw stdout than to wire up via real remotes.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from devfolder.git import (
    BranchSummary,
    WorkingTreeState,
    branches,
    get_git_remotes,
    last_commit_at,
    stash_count,
    status,
)

# --- helpers ---


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command with stable test config; raise on failure."""
    return subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(path: Path) -> None:
    """Initialise a fresh git repo with deterministic test config."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=path,
        check=True,
    )
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(path: Path, message: str = "test") -> None:
    """Stage everything in `path` and commit with `message`."""
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", message)


def _setup_remote_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Create a bare upstream repo and a working clone with origin set.

    Returns (work_path, upstream_path). Working clone has one initial
    commit on `main` with upstream tracking configured.
    """
    upstream = tmp_path / "upstream.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(upstream)],
        check=True,
    )

    work = tmp_path / "work"
    _init_repo(work)
    _git(work, "remote", "add", "origin", str(upstream))
    (work / "README.md").write_text("hello")
    _commit(work, "initial")
    _git(work, "push", "-q", "-u", "origin", "main")
    return work, upstream


# --- get_git_remotes (URL parsing — mock-based) ---


class TestGetGitRemotes:
    """URL-parsing edge cases for get_git_remotes."""

    def _mock_run(self, stdout: str, returncode: int = 0) -> MagicMock:
        mock_result = MagicMock()
        mock_result.stdout = stdout
        mock_result.returncode = returncode
        return mock_result

    def test_single_remote(self, tmp_path: Path) -> None:
        stdout = (
            "origin\tgit@github.com:user/repo.git (fetch)\n"
            "origin\tgit@github.com:user/repo.git (push)\n"
        )
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {"origin": "git@github.com:user/repo.git"}

    def test_multiple_remotes(self, tmp_path: Path) -> None:
        stdout = (
            "origin\tgit@github.com:user/repo.git (fetch)\n"
            "origin\tgit@github.com:user/repo.git (push)\n"
            "upstream\thttps://github.com/org/repo.git (fetch)\n"
            "upstream\thttps://github.com/org/repo.git (push)\n"
        )
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {
            "origin": "git@github.com:user/repo.git",
            "upstream": "https://github.com/org/repo.git",
        }

    def test_prefers_fetch_over_push(self, tmp_path: Path) -> None:
        """When fetch and push URLs differ, use the fetch URL."""
        stdout = (
            "origin\tgit@github.com:user/repo.git (fetch)\n"
            "origin\tgit@github.com:user/repo-push.git (push)\n"
        )
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            remotes = get_git_remotes(tmp_path)

        assert remotes["origin"] == "git@github.com:user/repo.git"

    def test_empty_output(self, tmp_path: Path) -> None:
        with patch("subprocess.run", return_value=self._mock_run("")):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}

    def test_nonzero_return_code(self, tmp_path: Path) -> None:
        mock = self._mock_run("", returncode=128)
        with patch("subprocess.run", return_value=mock):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}

    def test_subprocess_error(self, tmp_path: Path) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("git not found"),
        ):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}

    def test_os_error(self, tmp_path: Path) -> None:
        with patch(
            "subprocess.run",
            side_effect=OSError("no such file"),
        ):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}


# --- status (real fixture repos) ---


class TestStatus:
    """Working tree state via real git fixtures."""

    def test_clean_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "clean"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)

        assert status(repo) == WorkingTreeState(
            clean=True, staged=0, modified=0, untracked=0
        )

    def test_untracked_files(self, tmp_path: Path) -> None:
        repo = tmp_path / "untracked"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        (repo / "new1.txt").write_text("x")
        (repo / "new2.txt").write_text("y")

        result = status(repo)
        assert not result.clean
        assert result.untracked == 2
        assert result.staged == 0
        assert result.modified == 0

    def test_modified_files(self, tmp_path: Path) -> None:
        repo = tmp_path / "modified"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        (repo / "a.txt").write_text("changed")

        result = status(repo)
        assert not result.clean
        assert result.modified == 1
        assert result.staged == 0
        assert result.untracked == 0

    def test_staged_files(self, tmp_path: Path) -> None:
        repo = tmp_path / "staged"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        (repo / "b.txt").write_text("b")
        _git(repo, "add", "b.txt")

        result = status(repo)
        assert not result.clean
        assert result.staged == 1
        assert result.modified == 0
        assert result.untracked == 0

    def test_mixed_state(self, tmp_path: Path) -> None:
        repo = tmp_path / "mixed"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        (repo / "b.txt").write_text("b")
        _commit(repo)

        # Modify a.txt (modified)
        (repo / "a.txt").write_text("a-changed")
        # Stage a new file (staged)
        (repo / "c.txt").write_text("c")
        _git(repo, "add", "c.txt")
        # Add another untracked file (untracked)
        (repo / "d.txt").write_text("d")

        result = status(repo)
        assert not result.clean
        assert result.staged == 1
        assert result.modified == 1
        assert result.untracked == 1

    def test_non_git_directory(self, tmp_path: Path) -> None:
        """A directory that isn't a git repo returns a default-clean state."""
        result = status(tmp_path)
        assert result == WorkingTreeState(
            clean=True, staged=0, modified=0, untracked=0
        )


# --- branches (real fixture repos) ---


class TestBranches:
    """Branch summary via real git fixtures."""

    def test_empty_repo(self, tmp_path: Path) -> None:
        """A repo with no commits has no branches."""
        repo = tmp_path / "empty"
        _init_repo(repo)

        assert branches(repo) == BranchSummary(
            total=0, no_upstream=0, ahead_of_upstream=0
        )

    def test_single_branch_no_upstream(self, tmp_path: Path) -> None:
        repo = tmp_path / "lonely"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)

        assert branches(repo) == BranchSummary(
            total=1, no_upstream=1, ahead_of_upstream=0
        )

    def test_branch_with_upstream_up_to_date(self, tmp_path: Path) -> None:
        work, _ = _setup_remote_pair(tmp_path)

        assert branches(work) == BranchSummary(
            total=1, no_upstream=0, ahead_of_upstream=0
        )

    def test_branch_ahead_of_upstream(self, tmp_path: Path) -> None:
        work, _ = _setup_remote_pair(tmp_path)
        (work / "more.txt").write_text("more")
        _commit(work, "second")

        result = branches(work)
        assert result.total == 1
        assert result.no_upstream == 0
        assert result.ahead_of_upstream == 1

    def test_multiple_branches_mixed_upstream(self, tmp_path: Path) -> None:
        work, _ = _setup_remote_pair(tmp_path)
        # Add a second local-only branch
        _git(work, "branch", "feature")

        result = branches(work)
        assert result.total == 2
        assert result.no_upstream == 1  # only feature lacks upstream
        assert result.ahead_of_upstream == 0

    def test_non_git_directory(self, tmp_path: Path) -> None:
        result = branches(tmp_path)
        assert result == BranchSummary(
            total=0, no_upstream=0, ahead_of_upstream=0
        )


# --- stash_count (real fixture repos) ---


class TestStashCount:
    """Stash counting via real git fixtures."""

    def test_no_stash(self, tmp_path: Path) -> None:
        repo = tmp_path / "nostash"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)

        assert stash_count(repo) == 0

    def test_single_stash(self, tmp_path: Path) -> None:
        repo = tmp_path / "stashed"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        (repo / "a.txt").write_text("dirty")
        _git(repo, "stash", "push", "-m", "wip")

        assert stash_count(repo) == 1

    def test_multiple_stashes(self, tmp_path: Path) -> None:
        repo = tmp_path / "many-stashes"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        for i in range(3):
            (repo / "a.txt").write_text(f"dirty {i}")
            _git(repo, "stash", "push", "-m", f"wip {i}")

        assert stash_count(repo) == 3

    def test_non_git_directory(self, tmp_path: Path) -> None:
        assert stash_count(tmp_path) == 0


# --- last_commit_at (real fixture repos) ---


class TestLastCommitAt:
    """Last-commit timestamp via real git fixtures."""

    def test_empty_repo_returns_none(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty"
        _init_repo(repo)

        assert last_commit_at(repo) is None

    def test_repo_with_commit_returns_tz_aware_datetime(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "with-commit"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)

        result = last_commit_at(repo)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo is not None  # tz-aware

    def test_non_git_directory_returns_none(self, tmp_path: Path) -> None:
        assert last_commit_at(tmp_path) is None


# --- detached HEAD doesn't break anything ---


class TestDetachedHead:
    """Detached HEAD shouldn't skew branch/status/stash counts.

    The branches() function iterates refs/heads/ which is independent
    of HEAD's position. status() and stash_count() are also unaffected.
    """

    def test_branches_with_detached_head(self, tmp_path: Path) -> None:
        repo = tmp_path / "detached"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        # Detach by checking out the commit SHA directly
        sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
        _git(repo, "checkout", "-q", sha)

        # Still one branch (main); detached HEAD doesn't add or remove branches
        result = branches(repo)
        assert result.total == 1

    def test_status_clean_in_detached_head(self, tmp_path: Path) -> None:
        repo = tmp_path / "detached-clean"
        _init_repo(repo)
        (repo / "a.txt").write_text("a")
        _commit(repo)
        sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
        _git(repo, "checkout", "-q", sha)

        assert status(repo).clean
