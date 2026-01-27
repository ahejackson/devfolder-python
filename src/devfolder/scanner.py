"""Directory scanning logic for devfolder."""

from pathlib import Path

from .classifier import classify_project, has_git_directory
from .config import Config
from .models import (
    CategoryNode,
    ErrorNode,
    IgnoredNode,
    IgnoreReason,
    Node,
    ScanResult,
    SymlinkNode,
)


def should_ignore(entry: Path) -> IgnoreReason | None:
    """Check if an entry should be ignored.

    Args:
        entry: The directory entry to check.

    Returns:
        The ignore reason if it should be ignored, None otherwise.
    """
    name = entry.name

    if name.startswith("."):
        return IgnoreReason.DOTFOLDER

    if name == "node_modules":
        return IgnoreReason.NODE_MODULES

    return None


def scan_category(category_path: Path, config: Config) -> list[Node]:
    """Scan a category directory for projects.

    Args:
        category_path: Path to the category directory.
        config: Configuration for classification.

    Returns:
        A list of nodes representing the category's contents.
    """
    children: list[Node] = []

    try:
        entries = sorted(category_path.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as e:
        return [
            ErrorNode(
                name=category_path.name,
                path=category_path,
                error_message=str(e),
            )
        ]
    except OSError as e:
        return [
            ErrorNode(
                name=category_path.name,
                path=category_path,
                error_message=str(e),
            )
        ]

    for entry in entries:
        # Handle symlinks (don't follow them)
        if entry.is_symlink():
            try:
                target = entry.resolve()
            except OSError:
                target = None
            children.append(
                SymlinkNode(
                    name=entry.name,
                    path=entry,
                    target=target,
                )
            )
            continue

        # Skip non-directories
        if not entry.is_dir():
            continue

        # Check if should be ignored
        if (reason := should_ignore(entry)) is not None:
            children.append(
                IgnoredNode(
                    name=entry.name,
                    path=entry,
                    reason=reason,
                )
            )
            continue

        # All other directories at this level are projects
        try:
            project = classify_project(entry, config)
            children.append(project)
        except PermissionError as e:
            children.append(
                ErrorNode(
                    name=entry.name,
                    path=entry,
                    error_message=str(e),
                )
            )
        except OSError as e:
            children.append(
                ErrorNode(
                    name=entry.name,
                    path=entry,
                    error_message=str(e),
                )
            )

    return children


def scan(root: Path, config: Config) -> ScanResult:
    """Scan a directory tree for projects.

    Args:
        root: The root directory to scan.
        config: Configuration for classification.

    Returns:
        A ScanResult containing the directory tree structure.
    """
    root = root.resolve()

    # Check if root itself is a project
    if has_git_directory(root):
        project = classify_project(root, config)
        return ScanResult(
            root=root,
            children=(),
            root_project=project,
        )

    children: list[Node] = []

    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as e:
        return ScanResult(
            root=root,
            children=(
                ErrorNode(
                    name=root.name,
                    path=root,
                    error_message=str(e),
                ),
            ),
        )
    except OSError as e:
        return ScanResult(
            root=root,
            children=(
                ErrorNode(
                    name=root.name,
                    path=root,
                    error_message=str(e),
                ),
            ),
        )

    for entry in entries:
        # Handle symlinks (don't follow them)
        if entry.is_symlink():
            try:
                target = entry.resolve()
            except OSError:
                target = None
            children.append(
                SymlinkNode(
                    name=entry.name,
                    path=entry,
                    target=target,
                )
            )
            continue

        # Skip non-directories
        if not entry.is_dir():
            continue

        # Check if should be ignored
        if (reason := should_ignore(entry)) is not None:
            children.append(
                IgnoredNode(
                    name=entry.name,
                    path=entry,
                    reason=reason,
                )
            )
            continue

        # Check if this is a project at category level
        try:
            if has_git_directory(entry):
                project = classify_project(entry, config)
                children.append(project)
                continue
        except (PermissionError, OSError):
            pass

        # Otherwise, treat as a category
        try:
            category_children = scan_category(entry, config)
            children.append(
                CategoryNode(
                    name=entry.name,
                    path=entry,
                    children=tuple(category_children),
                )
            )
        except PermissionError as e:
            children.append(
                ErrorNode(
                    name=entry.name,
                    path=entry,
                    error_message=str(e),
                )
            )
        except OSError as e:
            children.append(
                ErrorNode(
                    name=entry.name,
                    path=entry,
                    error_message=str(e),
                )
            )

    return ScanResult(
        root=root,
        children=tuple(children),
    )
