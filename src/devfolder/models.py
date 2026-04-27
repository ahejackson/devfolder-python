"""Data models for devfolder."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

__all__ = [
    "BareGitInspectResult",
    "BranchSummary",
    "CategoryNode",
    "ErrorNode",
    "GitInspectResult",
    "GitLayout",
    "IgnoredNode",
    "IgnoreReason",
    "LinkedRepo",
    "LinkedRepoKind",
    "Node",
    "NodeKind",
    "NonGitInspectResult",
    "Owner",
    "ProjectNode",
    "ProjectType",
    "RemoteRecord",
    "ScanResult",
    "SymlinkNode",
    "WorkingTreeState",
]


class NodeKind(Enum):
    """The kind of node in the directory tree."""

    PROJECT = "project"
    CATEGORY = "category"
    SYMLINK = "symlink"
    IGNORED = "ignored"
    ERROR = "error"


class ProjectType(Enum):
    """Classification of a project based on git status."""

    EMPTY = "empty"
    LOCAL_UNTRACKED = "local-untracked"
    LOCAL_GIT = "local-git"
    OWNED_REMOTE = "owned-remote"
    OTHER_REMOTE = "other-remote"


class GitLayout(Enum):
    """Physical layout of a git project's metadata.

    `WORKING_TREE` is the standard layout (`.git/` directory inside
    the project). `LINKED` is the worktree/submodule shape — `.git`
    is a file containing a `gitdir:` pointer. `BARE` is a bare
    repository where the project directory itself holds the git
    data and there is no working tree.
    """

    WORKING_TREE = "working-tree"
    LINKED = "linked"
    BARE = "bare"


@dataclass(frozen=True)
class Owner:
    """A remote owner identity (host + name) used for project classification."""

    name: str
    host: str


class IgnoreReason(Enum):
    """Reason why a folder was ignored."""

    DOTFOLDER = "dotfolder"
    NODE_MODULES = "node_modules"


@dataclass(frozen=True)
class Node:
    """Base class for all nodes in the directory tree."""

    name: str
    path: Path
    kind: NodeKind


@dataclass(frozen=True)
class ProjectNode(Node):
    """A project folder."""

    project_type: ProjectType
    remote_url: str | None = None
    owner: str | None = None
    git_layout: GitLayout | None = None

    def __init__(
        self,
        name: str,
        path: Path,
        project_type: ProjectType,
        remote_url: str | None = None,
        owner: str | None = None,
        git_layout: GitLayout | None = None,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "kind", NodeKind.PROJECT)
        object.__setattr__(self, "project_type", project_type)
        object.__setattr__(self, "remote_url", remote_url)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "git_layout", git_layout)


@dataclass(frozen=True)
class CategoryNode(Node):
    """A category folder containing projects."""

    children: tuple[Node, ...] = field(default_factory=tuple)

    def __init__(
        self,
        name: str,
        path: Path,
        children: tuple[Node, ...] | None = None,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "kind", NodeKind.CATEGORY)
        object.__setattr__(self, "children", children if children is not None else ())

    @property
    def is_empty(self) -> bool:
        """Check if the category has no project children."""
        return len(self.children) == 0


@dataclass(frozen=True)
class SymlinkNode(Node):
    """A symbolic link."""

    target: Path | None = None

    def __init__(
        self,
        name: str,
        path: Path,
        target: Path | None = None,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "kind", NodeKind.SYMLINK)
        object.__setattr__(self, "target", target)


@dataclass(frozen=True)
class IgnoredNode(Node):
    """An ignored folder."""

    reason: IgnoreReason = IgnoreReason.DOTFOLDER

    def __init__(
        self,
        name: str,
        path: Path,
        reason: IgnoreReason = IgnoreReason.DOTFOLDER,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "kind", NodeKind.IGNORED)
        object.__setattr__(self, "reason", reason)


@dataclass(frozen=True)
class ErrorNode(Node):
    """A folder that could not be scanned due to an error."""

    error_message: str = ""

    def __init__(
        self,
        name: str,
        path: Path,
        error_message: str = "",
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "kind", NodeKind.ERROR)
        object.__setattr__(self, "error_message", error_message)


@dataclass(frozen=True)
class ScanResult:
    """The result of scanning a directory tree."""

    root: Path
    children: tuple[Node, ...]
    root_project: ProjectNode | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_root_project(self) -> bool:
        """Check if the root directory itself is a project."""
        return self.root_project is not None


@dataclass(frozen=True)
class WorkingTreeState:
    """Summary of `git status` output for a working tree."""

    clean: bool
    staged: int
    modified: int
    untracked: int


@dataclass(frozen=True)
class BranchSummary:
    """Summary of local branches and their upstream relationships."""

    total: int
    no_upstream: int
    ahead_of_upstream: int


@dataclass(frozen=True)
class RemoteRecord:
    """A git remote with its decomposed URL parts.

    `host`, `owner`, and `repo` are None when the URL can't be parsed
    (e.g. unfamiliar URL shape).
    """

    name: str
    url: str
    host: str | None
    owner: str | None
    repo: str | None


class LinkedRepoKind(Enum):
    """The kind of repo a linked project is connected to."""

    WORKTREE = "worktree"
    SUBMODULE = "submodule"


@dataclass(frozen=True)
class LinkedRepo:
    """Information about the repo a linked project is connected to.

    For worktrees, this is the main checkout. For submodules, it is
    the superproject's working tree.
    """

    kind: LinkedRepoKind
    linked_repo_path: Path


@dataclass(frozen=True)
class GitInspectResult:
    """Per-project inspect output for a git project with a working tree."""

    path: Path
    gitdir: Path
    linked_to: LinkedRepo | None
    working_tree: WorkingTreeState
    branches: BranchSummary
    stash_count: int
    last_commit_at: datetime | None
    mtime: datetime
    remotes: tuple[RemoteRecord, ...]
    scanned_at: datetime


@dataclass(frozen=True)
class BareGitInspectResult:
    """Per-project inspect output for a bare git repository.

    Bare repos lack a working tree, so the `working_tree` and
    `linked_to` fields are absent. The project path itself is the
    gitdir.
    """

    path: Path
    branches: BranchSummary
    stash_count: int
    last_commit_at: datetime | None
    mtime: datetime
    remotes: tuple[RemoteRecord, ...]
    scanned_at: datetime


@dataclass(frozen=True)
class NonGitInspectResult:
    """Per-project inspect output for a non-git project (untracked or empty)."""

    path: Path
    file_count: int
    folder_count: int
    total_size_bytes: int
    mtime: datetime
    scanned_at: datetime
