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

__all__ = ["is_nested_category", "scan", "scan_category", "should_ignore"]


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


def _make_error_node(entry: Path, error: OSError) -> ErrorNode:
    """Create an ErrorNode from a path and an OS error.

    Args:
        entry: The path that caused the error.
        error: The OS error that occurred.

    Returns:
        An ErrorNode recording the error.
    """
    return ErrorNode(name=entry.name, path=entry, error_message=str(error))


def _try_symlink_node(entry: Path) -> SymlinkNode | None:
    """Create a SymlinkNode if the entry is a symlink to a directory.

    Args:
        entry: The directory entry to check.

    Returns:
        A SymlinkNode if the entry is a symlink to a directory, None otherwise.
    """
    if not entry.is_symlink():
        return None

    if not entry.is_dir():
        return None

    try:
        target = entry.resolve()
    except OSError:
        target = None

    return SymlinkNode(name=entry.name, path=entry, target=target)


def is_nested_category(path: Path) -> bool:
    """Check if a directory should be treated as a nested category.

    A directory is a nested category if:
    1. It is not a git repository.
    2. It contains only other directories (and possibly dotfiles).
    3. At least one of its subdirectories is a git repository.

    Args:
        path: The directory to check.

    Returns:
        True if it's a nested category, False otherwise.
    """
    if has_git_directory(path):
        return False

    try:
        entries = list(path.iterdir())
        if not entries:
            return False

        has_git_child = False
        for entry in entries:
            # Ignore dotfiles
            if entry.name.startswith("."):
                continue

            # If there's any non-directory, it's not a category
            if not entry.is_dir():
                return False

            # Check if any child is a git repo
            if has_git_directory(entry):
                has_git_child = True

        return has_git_child
    except OSError:
        return False


def scan_category(
    category_path: Path, config: Config, allow_nested: bool = True
) -> list[Node]:
    """Scan a category directory for projects.

    Args:
        category_path: Path to the category directory.
        config: Configuration for classification.
        allow_nested: Whether to allow nested categories.

    Returns:
        A list of nodes representing the category's contents.
    """
    children: list[Node] = []

    try:
        entries = sorted(category_path.iterdir(), key=lambda p: p.name.lower())
    except OSError as e:
        return [_make_error_node(category_path, e)]

    for entry in entries:
        # Handle symlinks to directories (don't follow them)
        if entry.is_symlink():
            if (symlink := _try_symlink_node(entry)) is not None:
                children.append(symlink)
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

        # Check for nested category
        if allow_nested and is_nested_category(entry):
            try:
                # Nested categories don't allow further nesting for now
                category_children = scan_category(entry, config, allow_nested=False)
                children.append(
                    CategoryNode(
                        name=entry.name,
                        path=entry,
                        children=tuple(category_children),
                    )
                )
                continue
            except OSError as e:
                children.append(_make_error_node(entry, e))
                continue

        # All other directories at this level are projects
        try:
            project = classify_project(entry, config)
            children.append(project)
        except OSError as e:
            children.append(_make_error_node(entry, e))

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
    except OSError as e:
        return ScanResult(
            root=root,
            children=(_make_error_node(root, e),),
        )

    for entry in entries:
        # Handle symlinks to directories (don't follow them)
        if entry.is_symlink():
            if (symlink := _try_symlink_node(entry)) is not None:
                children.append(symlink)
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
        except OSError:
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
        except OSError as e:
            children.append(_make_error_node(entry, e))

    return ScanResult(
        root=root,
        children=tuple(children),
    )
