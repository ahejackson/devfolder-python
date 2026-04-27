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
    git_meta,
    last_commit_at,
    parse_remote,
    stash_count,
    status,
)
from devfolder.models import RemoteRecord

from .conftest import (
    git_commit,
    init_git_repo,
    run_git,
    setup_remote_pair,
)

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
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        assert status(repo) == WorkingTreeState(
            clean=True, staged=0, modified=0, untracked=0
        )

    def test_untracked_files(self, tmp_path: Path) -> None:
        repo = tmp_path / "untracked"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        (repo / "new1.txt").write_text("x")
        (repo / "new2.txt").write_text("y")

        result = status(repo)
        assert not result.clean
        assert result.untracked == 2
        assert result.staged == 0
        assert result.modified == 0

    def test_modified_files(self, tmp_path: Path) -> None:
        repo = tmp_path / "modified"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        (repo / "a.txt").write_text("changed")

        result = status(repo)
        assert not result.clean
        assert result.modified == 1
        assert result.staged == 0
        assert result.untracked == 0

    def test_staged_files(self, tmp_path: Path) -> None:
        repo = tmp_path / "staged"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        (repo / "b.txt").write_text("b")
        run_git(repo, "add", "b.txt")

        result = status(repo)
        assert not result.clean
        assert result.staged == 1
        assert result.modified == 0
        assert result.untracked == 0

    def test_mixed_state(self, tmp_path: Path) -> None:
        repo = tmp_path / "mixed"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        (repo / "b.txt").write_text("b")
        git_commit(repo)

        # Modify a.txt (modified)
        (repo / "a.txt").write_text("a-changed")
        # Stage a new file (staged)
        (repo / "c.txt").write_text("c")
        run_git(repo, "add", "c.txt")
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
        init_git_repo(repo)

        assert branches(repo) == BranchSummary(
            total=0, no_upstream=0, ahead_of_upstream=0
        )

    def test_single_branch_no_upstream(self, tmp_path: Path) -> None:
        repo = tmp_path / "lonely"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        assert branches(repo) == BranchSummary(
            total=1, no_upstream=1, ahead_of_upstream=0
        )

    def test_branch_with_upstream_up_to_date(self, tmp_path: Path) -> None:
        work, _ = setup_remote_pair(tmp_path)

        assert branches(work) == BranchSummary(
            total=1, no_upstream=0, ahead_of_upstream=0
        )

    def test_branch_ahead_of_upstream(self, tmp_path: Path) -> None:
        work, _ = setup_remote_pair(tmp_path)
        (work / "more.txt").write_text("more")
        git_commit(work, "second")

        result = branches(work)
        assert result.total == 1
        assert result.no_upstream == 0
        assert result.ahead_of_upstream == 1

    def test_multiple_branches_mixed_upstream(self, tmp_path: Path) -> None:
        work, _ = setup_remote_pair(tmp_path)
        # Add a second local-only branch
        run_git(work, "branch", "feature")

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
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        assert stash_count(repo) == 0

    def test_single_stash(self, tmp_path: Path) -> None:
        repo = tmp_path / "stashed"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        (repo / "a.txt").write_text("dirty")
        run_git(repo, "stash", "push", "-m", "wip")

        assert stash_count(repo) == 1

    def test_multiple_stashes(self, tmp_path: Path) -> None:
        repo = tmp_path / "many-stashes"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        for i in range(3):
            (repo / "a.txt").write_text(f"dirty {i}")
            run_git(repo, "stash", "push", "-m", f"wip {i}")

        assert stash_count(repo) == 3

    def test_non_git_directory(self, tmp_path: Path) -> None:
        assert stash_count(tmp_path) == 0


# --- last_commit_at (real fixture repos) ---


class TestLastCommitAt:
    """Last-commit timestamp via real git fixtures."""

    def test_empty_repo_returns_none(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty"
        init_git_repo(repo)

        assert last_commit_at(repo) is None

    def test_repo_with_commit_returns_tz_aware_datetime(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "with-commit"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

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
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        # Detach by checking out the commit SHA directly
        sha = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        run_git(repo, "checkout", "-q", sha)

        # Still one branch (main); detached HEAD doesn't add or remove branches
        result = branches(repo)
        assert result.total == 1

    def test_status_clean_in_detached_head(self, tmp_path: Path) -> None:
        repo = tmp_path / "detached-clean"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        sha = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        run_git(repo, "checkout", "-q", sha)

        assert status(repo).clean


# --- parse_remote ---


class TestParseRemote:
    """URL → RemoteRecord parsing."""

    def test_ssh_with_git_suffix(self) -> None:
        result = parse_remote(
            "origin", "git@github.com:ahejackson/devfolder.git"
        )
        assert result == RemoteRecord(
            name="origin",
            url="git@github.com:ahejackson/devfolder.git",
            host="github.com",
            owner="ahejackson",
            repo="devfolder",
        )

    def test_ssh_without_git_suffix(self) -> None:
        result = parse_remote("origin", "git@gitlab.com:org/proj")
        assert result.host == "gitlab.com"
        assert result.owner == "org"
        assert result.repo == "proj"

    def test_https_url(self) -> None:
        result = parse_remote(
            "upstream", "https://github.com/microsoft/RustTraining.git"
        )
        assert result.host == "github.com"
        assert result.owner == "microsoft"
        assert result.repo == "RustTraining"

    def test_git_protocol(self) -> None:
        result = parse_remote("origin", "git://example.com/owner/repo.git")
        assert result.host == "example.com"
        assert result.owner == "owner"
        assert result.repo == "repo"

    def test_unparseable_url_returns_nones(self) -> None:
        result = parse_remote("origin", "not-a-url")
        assert result.name == "origin"
        assert result.url == "not-a-url"
        assert result.host is None
        assert result.owner is None
        assert result.repo is None

    def test_url_with_only_owner_no_repo(self) -> None:
        """SSH-style URL missing the repo part still yields owner."""
        result = parse_remote("origin", "git@github.com:ahejackson")
        assert result.host == "github.com"
        assert result.owner == "ahejackson"
        assert result.repo is None

    def test_repo_name_kept_intact_when_not_dotgit(self) -> None:
        """A repo name that ends in something other than `.git` is kept."""
        result = parse_remote(
            "origin", "https://github.com/owner/some.repo"
        )
        assert result.repo == "some.repo"


# --- git_meta ---


class TestGitMeta:
    """Layout/linkage probe via `git rev-parse`."""

    def test_working_tree_project(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_git_repo(repo)
        meta = git_meta(repo)
        assert meta is not None
        assert meta.is_bare is False
        assert meta.gitdir == (repo / ".git").resolve()
        assert meta.gitdir == meta.common_dir
        assert meta.superproject_path is None

    def test_bare_repo(self, bare_git_project: Path) -> None:
        meta = git_meta(bare_git_project)
        assert meta is not None
        assert meta.is_bare is True
        assert meta.gitdir == bare_git_project.resolve()
        assert meta.superproject_path is None

    def test_worktree(
        self, worktree_project: tuple[Path, Path]
    ) -> None:
        wt, main = worktree_project
        meta = git_meta(wt)
        assert meta is not None
        assert meta.is_bare is False
        # gitdir is the worktree's per-checkout dir; common_dir is the
        # main repo's gitdir; they differ for a worktree.
        assert meta.gitdir != meta.common_dir
        assert meta.common_dir == (main / ".git").resolve()
        assert meta.superproject_path is None

    def test_submodule(
        self, submodule_project: tuple[Path, Path]
    ) -> None:
        sub, parent = submodule_project
        meta = git_meta(sub)
        assert meta is not None
        assert meta.is_bare is False
        assert meta.superproject_path is not None
        assert meta.superproject_path.resolve() == parent.resolve()

    def test_non_git_path_returns_none(self, tmp_path: Path) -> None:
        d = tmp_path / "not-a-repo"
        d.mkdir()
        meta = git_meta(d)
        assert meta is None
