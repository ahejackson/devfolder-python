"""Report logic: scan a tree and inspect every project sequentially.

`run_report` produces an augmented JSON-ready dict — the existing
ScanResult shape, with each ProjectNode gaining an `inspect` field
populated by `inspector.inspect()`.

Designed for the salvage-laptop use case: one big sweep that surfaces
everything you might need to act on (unpushed work, untracked branches,
uncommitted changes, recent activity) in a single document.
"""

from collections.abc import Callable
from pathlib import Path

from .config import Config
from .inspector import inspect
from .models import Node, NodeKind, ProjectNode, ScanResult
from .scanner import scan
from .serializers import inspect_to_dict, scan_result_to_dict

__all__ = ["ProgressCallback", "run_report"]

# (current_index, total, path) — current_index is 1-based.
ProgressCallback = Callable[[int, int, Path], None]


def run_report(
    root: Path,
    config: Config,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    """Scan `root`, inspect every project, return the augmented JSON dict.

    Args:
        root: Directory to scan.
        config: Devfolder configuration (used by scan for owner matching).
        on_progress: Optional callback invoked once per project before
            its inspect runs. Receives `(current, total, project_path)`.

    Returns:
        A JSON-ready dict matching the ScanResult shape with `inspect`
        fields embedded on every ProjectNode.
    """
    scan_result = scan(root, config)
    project_paths = _collect_project_paths(scan_result)
    total = len(project_paths)

    inspect_by_path: dict[Path, dict[str, object]] = {}
    for index, path in enumerate(project_paths, start=1):
        if on_progress is not None:
            on_progress(index, total, path)
        inspect_by_path[path] = inspect_to_dict(inspect(path))

    return scan_result_to_dict(scan_result, inspect_by_path)


def _collect_project_paths(result: ScanResult) -> list[Path]:
    """Walk a ScanResult and return every ProjectNode's path."""
    paths: list[Path] = []
    if result.root_project is not None:
        paths.append(result.root_project.path)
    for child in result.children:
        _collect_from_node(child, paths)
    return paths


def _collect_from_node(node: Node, paths: list[Path]) -> None:
    """Recurse a node tree, appending project paths in encounter order."""
    if node.kind == NodeKind.PROJECT:
        assert isinstance(node, ProjectNode)
        paths.append(node.path)
        return
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children:
        _collect_from_node(child, paths)
