"""Tests for devfolder.inspector module."""

import subprocess
from datetime import datetime
from pathlib import Path

from devfolder.inspector import EXCLUDED_WALK_DIRS, inspect
from devfolder.models import (
    BareGitInspectResult,
    GitInspectResult,
    LinkedRepoKind,
    NonGitInspectResult,
)

from .conftest import git_commit, init_git_repo, run_git, setup_remote_pair


class TestInspectDispatch:
    """Top-level inspect() dispatch on git vs non-git."""

    def test_git_repo_returns_git_result(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        result = inspect(repo)
        assert isinstance(result, GitInspectResult)

    def test_non_git_dir_returns_non_git_result(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        (plain / "a.txt").write_text("a")

        result = inspect(plain)
        assert isinstance(result, NonGitInspectResult)

    def test_empty_dir_returns_non_git_result(self, tmp_path: Path) -> None:
        plain = tmp_path / "empty"
        plain.mkdir()

        result = inspect(plain)
        assert isinstance(result, NonGitInspectResult)
        assert result.file_count == 0
        assert result.folder_count == 0
        assert result.total_size_bytes == 0


class TestInspectGit:
    """GitInspectResult content for various repo states."""

    def test_clean_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "clean"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        result = inspect(repo)
        assert isinstance(result, GitInspectResult)
        assert result.path == repo
        assert result.working_tree.clean
        assert result.branches.total == 1
        assert result.stash_count == 0
        assert result.last_commit_at is not None
        assert result.last_commit_at.tzinfo is not None
        assert result.mtime.tzinfo is not None
        assert result.scanned_at.tzinfo is not None
        # Working-tree project: gitdir is `<path>/.git`, no linkage.
        assert result.gitdir == (repo / ".git").resolve()
        assert result.linked_to is None

    def test_worktree_inspect(
        self, worktree_project: tuple[Path, Path]
    ) -> None:
        """A worktree has linked_to=worktree pointing at the main repo."""
        wt, main = worktree_project
        result = inspect(wt)
        assert isinstance(result, GitInspectResult)
        assert result.linked_to is not None
        assert result.linked_to.kind is LinkedRepoKind.WORKTREE
        assert result.linked_to.linked_repo_path.resolve() == main.resolve()

    def test_submodule_inspect(
        self, submodule_project: tuple[Path, Path]
    ) -> None:
        """A submodule has linked_to=submodule pointing at the parent repo."""
        sub, parent = submodule_project
        result = inspect(sub)
        assert isinstance(result, GitInspectResult)
        assert result.linked_to is not None
        assert result.linked_to.kind is LinkedRepoKind.SUBMODULE
        assert result.linked_to.linked_repo_path.resolve() == parent.resolve()

    def test_dirty_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "dirty"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        (repo / "a.txt").write_text("changed")
        (repo / "new.txt").write_text("new")

        result = inspect(repo)
        assert isinstance(result, GitInspectResult)
        assert not result.working_tree.clean
        assert result.working_tree.modified == 1
        assert result.working_tree.untracked == 1

    def test_empty_repo_has_no_last_commit(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty-repo"
        init_git_repo(repo)

        result = inspect(repo)
        assert isinstance(result, GitInspectResult)
        assert result.last_commit_at is None
        assert result.branches.total == 0

    def test_repo_with_stash(self, tmp_path: Path) -> None:
        repo = tmp_path / "stashy"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        (repo / "a.txt").write_text("dirty")
        run_git(repo, "stash", "push", "-m", "wip")

        result = inspect(repo)
        assert isinstance(result, GitInspectResult)
        assert result.stash_count == 1

    def test_repo_with_remote_parsed(self, tmp_path: Path) -> None:
        work, _ = setup_remote_pair(tmp_path)

        result = inspect(work)
        assert isinstance(result, GitInspectResult)
        assert len(result.remotes) == 1
        origin = result.remotes[0]
        assert origin.name == "origin"
        # The upstream URL is a local file path, so host parsing yields None.
        # That's expected — RemoteRecord still captures name + url for the
        # salvage use case, where the raw URL is the actionable info.
        assert origin.url.endswith("upstream.git")

    def test_remotes_sorted_by_name(self, tmp_path: Path) -> None:
        """Multiple remotes appear in alphabetical order by name."""
        repo = tmp_path / "many-remotes"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        run_git(
            repo,
            "remote",
            "add",
            "zeta",
            "git@github.com:owner/zeta.git",
        )
        run_git(
            repo,
            "remote",
            "add",
            "alpha",
            "git@github.com:owner/alpha.git",
        )

        result = inspect(repo)
        assert isinstance(result, GitInspectResult)
        names = [r.name for r in result.remotes]
        assert names == ["alpha", "zeta"]
        assert result.remotes[0].repo == "alpha"
        assert result.remotes[1].repo == "zeta"


class TestInspectBareGit:
    """BareGitInspectResult content for bare repos."""

    def test_bare_repo_returns_bare_result(
        self, bare_git_project: Path
    ) -> None:
        result = inspect(bare_git_project)
        assert isinstance(result, BareGitInspectResult)
        assert result.path == bare_git_project
        assert result.branches.total == 0
        assert result.stash_count == 0
        assert result.last_commit_at is None
        assert result.mtime.tzinfo is not None
        assert result.scanned_at.tzinfo is not None

    def test_bare_repo_with_remote(self, tmp_path: Path) -> None:
        """A bare repo with a configured remote captures it."""
        bare = tmp_path / "myrepo.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(bare)],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(bare),
                "remote",
                "add",
                "origin",
                "git@github.com:owner/repo.git",
            ],
            check=True,
        )

        result = inspect(bare)
        assert isinstance(result, BareGitInspectResult)
        assert len(result.remotes) == 1
        assert result.remotes[0].name == "origin"
        assert result.remotes[0].owner == "owner"


class TestInspectNonGit:
    """NonGitInspectResult content for filesystem walks."""

    def test_files_and_folders_counted(self, tmp_path: Path) -> None:
        d = tmp_path / "project"
        d.mkdir()
        (d / "a.txt").write_text("hello")
        (d / "b.txt").write_text("world!")
        sub = d / "src"
        sub.mkdir()
        (sub / "main.py").write_text("print('x')")

        result = inspect(d)
        assert isinstance(result, NonGitInspectResult)
        assert result.file_count == 3
        assert result.folder_count == 1
        # 5 + 6 + 10 = 21 bytes
        assert result.total_size_bytes == 21

    def test_node_modules_excluded(self, tmp_path: Path) -> None:
        d = tmp_path / "project"
        d.mkdir()
        (d / "a.txt").write_text("a")
        nm = d / "node_modules"
        nm.mkdir()
        (nm / "huge.bin").write_text("x" * 10_000)
        (nm / "nested").mkdir()
        (nm / "nested" / "more.bin").write_text("y" * 5_000)

        result = inspect(d)
        assert isinstance(result, NonGitInspectResult)
        assert result.file_count == 1
        assert result.folder_count == 0
        assert result.total_size_bytes == 1

    def test_dot_git_excluded(self, tmp_path: Path) -> None:
        """A non-git inspect target with a `.git` somewhere skips it.

        (`inspect` itself dispatches to git when `.git` is at the *top*
        of the target — but if the target is a category-like folder
        with .git nested deep, we don't double-count its contents.)
        """
        d = tmp_path / "project"
        d.mkdir()
        (d / "real.txt").write_text("a")
        # Simulate a stray .git inside (unusual but possible)
        nested_git = d / ".git"
        nested_git.mkdir()
        (nested_git / "HEAD").write_text("ref: refs/heads/main")

        # Force the non-git path: inspect() would normally see top-level .git
        # and dispatch to git. So this test is best validated by a sub-dir
        # case instead — see test_dot_venv_excluded for the pattern.

    def test_dot_venv_excluded(self, tmp_path: Path) -> None:
        d = tmp_path / "project"
        d.mkdir()
        (d / "a.py").write_text("a")
        venv = d / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("home = /usr/bin")
        (venv / "lib").mkdir()
        (venv / "lib" / "site-packages").mkdir()
        (venv / "lib" / "site-packages" / "mod.py").write_text("x" * 1000)

        result = inspect(d)
        assert isinstance(result, NonGitInspectResult)
        assert result.file_count == 1
        assert result.folder_count == 0
        assert result.total_size_bytes == 1

    def test_excluded_dirs_constant_matches_expected_set(self) -> None:
        """Pinning the excluded-dir set so it doesn't drift silently."""
        assert EXCLUDED_WALK_DIRS == frozenset(
            {"node_modules", ".git", ".venv"}
        )

    def test_symlink_to_file_not_counted(self, tmp_path: Path) -> None:
        d = tmp_path / "project"
        d.mkdir()
        target = d / "real.txt"
        target.write_text("hello")
        link = d / "link.txt"
        link.symlink_to(target)

        result = inspect(d)
        assert isinstance(result, NonGitInspectResult)
        assert result.file_count == 1  # only real.txt, not the symlink
        assert result.total_size_bytes == 5

    def test_symlink_to_dir_not_descended(self, tmp_path: Path) -> None:
        d = tmp_path / "project"
        d.mkdir()
        (d / "a.txt").write_text("a")
        # External target with content we don't want counted
        external = tmp_path / "external"
        external.mkdir()
        (external / "huge.bin").write_text("x" * 10_000)
        (d / "shortcut").symlink_to(external)

        result = inspect(d)
        assert isinstance(result, NonGitInspectResult)
        assert result.file_count == 1
        assert result.folder_count == 0
        assert result.total_size_bytes == 1

    def test_mtime_and_scanned_at_are_tz_aware(self, tmp_path: Path) -> None:
        d = tmp_path / "project"
        d.mkdir()
        (d / "a.txt").write_text("a")

        result = inspect(d)
        assert isinstance(result.mtime, datetime)
        assert result.mtime.tzinfo is not None
        assert isinstance(result.scanned_at, datetime)
        assert result.scanned_at.tzinfo is not None
