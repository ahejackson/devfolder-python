"""Shared test fixtures for devfolder tests."""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from devfolder.config import Config
from devfolder.models import Owner


def run_git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in `path`, raising on failure. Test-only helper."""
    return subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )


def init_git_repo(path: Path) -> None:
    """Initialise a fresh git repo at `path` with deterministic test config."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=path, check=True
    )
    run_git(path, "config", "user.email", "test@example.com")
    run_git(path, "config", "user.name", "Test User")
    run_git(path, "config", "commit.gpgsign", "false")


def git_commit(path: Path, message: str = "test") -> None:
    """Stage everything in `path` and commit with `message`."""
    run_git(path, "add", "-A")
    run_git(path, "commit", "-q", "-m", message)


def setup_remote_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Create a bare upstream + working clone with one initial commit pushed.

    Returns (work_path, upstream_path).
    """
    upstream = tmp_path / "upstream.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(upstream)],
        check=True,
    )

    work = tmp_path / "work"
    init_git_repo(work)
    run_git(work, "remote", "add", "origin", str(upstream))
    (work / "README.md").write_text("hello")
    git_commit(work, "initial")
    run_git(work, "push", "-q", "-u", "origin", "main")
    return work, upstream


@pytest.fixture(scope="session")
def config() -> Config:
    """A config with a single GitHub owner used across most tests."""
    return Config(owners=(Owner(name="testuser", host="github.com"),))


@pytest.fixture(scope="session")
def config_no_owners() -> Config:
    """A config with no owners configured."""
    return Config()


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """An empty directory."""
    d = tmp_path / "empty-project"
    d.mkdir()
    return d


@pytest.fixture
def untracked_project(tmp_path: Path) -> Path:
    """A project directory with files but no .git."""
    d = tmp_path / "untracked"
    d.mkdir()
    (d / "main.py").write_text("print('hello')")
    (d / "README.md").write_text("# Hello")
    return d


@pytest.fixture
def local_git_project(tmp_path: Path) -> Path:
    """A project directory with .git but no remotes."""
    d = tmp_path / "local-git"
    d.mkdir()
    (d / ".git").mkdir()
    (d / "main.py").write_text("print('hello')")
    return d


@pytest.fixture
def owned_remote_project(tmp_path: Path) -> Path:
    """A git project with a remote matching the configured owner."""
    d = tmp_path / "owned"
    d.mkdir()
    (d / ".git").mkdir()
    (d / "main.py").write_text("print('hello')")
    return d


@pytest.fixture
def other_remote_project(tmp_path: Path) -> Path:
    """A git project with a remote not matching any configured owner."""
    d = tmp_path / "other"
    d.mkdir()
    (d / ".git").mkdir()
    (d / "main.py").write_text("print('hello')")
    return d


@pytest.fixture
def dev_folder(tmp_path: Path) -> Path:
    """A realistic two-level dev folder structure.

    Structure:
        root/
        ├── tools/
        │   ├── my-tool/         (has .git, personal remote)
        │   └── other-tool/      (has .git, other remote)
        ├── experiments/          (empty category)
        ├── scratch/
        │   ├── notes/            (no .git, untracked project)
        │   └── empty-project/    (empty project)
        ├── .config/              (dotfolder, ignored)
        ├── node_modules/         (ignored)
        ├── git-at-root/          (has .git at category level)
        └── link -> tools/my-tool (symlink)
    """
    root = tmp_path / "dev"
    root.mkdir()

    # Category: tools
    tools = root / "tools"
    tools.mkdir()

    my_tool = tools / "my-tool"
    my_tool.mkdir()
    (my_tool / ".git").mkdir()
    (my_tool / "src").mkdir()

    other_tool = tools / "other-tool"
    other_tool.mkdir()
    (other_tool / ".git").mkdir()
    (other_tool / "src").mkdir()

    # Category: experiments (empty)
    experiments = root / "experiments"
    experiments.mkdir()

    # Category: scratch
    scratch = root / "scratch"
    scratch.mkdir()

    notes = scratch / "notes"
    notes.mkdir()
    (notes / "todo.txt").write_text("things to do")

    empty_project = scratch / "empty-project"
    empty_project.mkdir()

    # Ignored: dotfolder
    dotconfig = root / ".config"
    dotconfig.mkdir()

    # Ignored: node_modules
    node_modules = root / "node_modules"
    node_modules.mkdir()

    # Category-level project (has .git)
    git_at_root = root / "git-at-root"
    git_at_root.mkdir()
    (git_at_root / ".git").mkdir()
    (git_at_root / "README.md").write_text("# Project")

    # Symlink
    link = root / "link"
    link.symlink_to(my_tool)

    return root


@pytest.fixture
def bare_git_project(tmp_path: Path) -> Path:
    """A real bare git repository, created via `git init --bare`."""
    d = tmp_path / "myrepo.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(d)],
        check=True,
    )
    return d


@pytest.fixture
def root_is_project(tmp_path: Path) -> Path:
    """A root directory that is itself a git project."""
    root = tmp_path / "project-root"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "main.py").write_text("print('hello')")
    return root


@contextmanager
def make_remote_patch(
    remotes: dict[str, str],
) -> Iterator[None]:
    """Patch get_git_remotes with specific remotes.

    Args:
        remotes: Dictionary mapping remote names to URLs.

    Yields:
        None.
    """
    with patch(
        "devfolder.classifier.get_git_remotes",
        return_value=remotes,
    ):
        yield
