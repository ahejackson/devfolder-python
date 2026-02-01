"""Data models for devfolder."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

__all__ = [
    "CategoryNode",
    "ErrorNode",
    "IgnoredNode",
    "IgnoreReason",
    "Node",
    "NodeKind",
    "ProjectNode",
    "ProjectType",
    "ScanResult",
    "SymlinkNode",
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
    PERSONAL_REMOTE = "personal-remote"
    OTHER_REMOTE = "other-remote"


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

    def __init__(
        self,
        name: str,
        path: Path,
        project_type: ProjectType,
        remote_url: str | None = None,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "kind", NodeKind.PROJECT)
        object.__setattr__(self, "project_type", project_type)
        object.__setattr__(self, "remote_url", remote_url)


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

    @property
    def is_root_project(self) -> bool:
        """Check if the root directory itself is a project."""
        return self.root_project is not None
