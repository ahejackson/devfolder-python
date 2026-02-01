"""Shared test fixtures for devfolder tests."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from devfolder.config import Config


@pytest.fixture
def config() -> Config:
    """A config with a test username."""
    return Config(username="testuser")


@pytest.fixture
def config_no_username() -> Config:
    """A config with no username set."""
    return Config(username=None)


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
def personal_remote_project(tmp_path: Path) -> Path:
    """A git project with a remote matching the test username."""
    d = tmp_path / "personal"
    d.mkdir()
    (d / ".git").mkdir()
    (d / "main.py").write_text("print('hello')")
    return d


@pytest.fixture
def other_remote_project(tmp_path: Path) -> Path:
    """A git project with a remote not matching the test username."""
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
