"""JSON serialization for devfolder scan and inspect results."""

import json
from pathlib import Path

__all__ = [
    "format_inspect_json",
    "format_json",
    "inspect_to_dict",
    "node_to_dict",
    "scan_result_to_dict",
]

from .models import (
    CategoryNode,
    ErrorNode,
    GitInspectResult,
    IgnoredNode,
    Node,
    NodeKind,
    NonGitInspectResult,
    ProjectNode,
    ScanResult,
    SymlinkNode,
)


def node_to_dict(
    node: Node,
    inspect_by_path: dict[Path, dict[str, object]] | None = None,
) -> dict[str, object]:
    """Convert a node to a plain dictionary for JSON serialization.

    Args:
        node: The node to convert.
        inspect_by_path: Optional mapping from project path to its
            serialised inspect record. When provided, ProjectNodes
            gain an `inspect` field with the matched record (or None
            if the path isn't in the map). Used by the report
            subcommand to embed per-project inspect data.

    Returns:
        A dictionary representation of the node.
    """
    match node.kind:
        case NodeKind.PROJECT:
            assert isinstance(node, ProjectNode)
            d: dict[str, object] = {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "project_type": node.project_type.value,
                "remote_url": node.remote_url,
                "owner": node.owner,
            }
            if inspect_by_path is not None:
                d["inspect"] = inspect_by_path.get(node.path)
            return d

        case NodeKind.CATEGORY:
            assert isinstance(node, CategoryNode)
            return {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "is_empty": node.is_empty,
                "children": [
                    node_to_dict(child, inspect_by_path)
                    for child in node.children
                ],
            }

        case NodeKind.SYMLINK:
            assert isinstance(node, SymlinkNode)
            return {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "target": str(node.target) if node.target else None,
            }

        case NodeKind.IGNORED:
            assert isinstance(node, IgnoredNode)
            return {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "reason": node.reason.value,
            }

        case NodeKind.ERROR:
            assert isinstance(node, ErrorNode)
            return {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "error_message": node.error_message,
            }


def scan_result_to_dict(
    result: ScanResult,
    inspect_by_path: dict[Path, dict[str, object]] | None = None,
) -> dict[str, object]:
    """Convert a scan result to a plain dictionary for JSON serialization.

    Args:
        result: The scan result to convert.
        inspect_by_path: Optional mapping from project path to its
            serialised inspect record. When provided, every ProjectNode
            in the output gains an `inspect` field. See `node_to_dict`.

    Returns:
        A dictionary representation of the scan result.
    """
    root_project: dict[str, object] | None = None
    if result.root_project is not None:
        root_project = node_to_dict(result.root_project, inspect_by_path)

    return {
        "generated_at": result.generated_at.isoformat(),
        "root": str(result.root),
        "is_root_project": result.is_root_project,
        "root_project": root_project,
        "children": [
            node_to_dict(child, inspect_by_path) for child in result.children
        ],
    }


def format_json(result: ScanResult) -> str:
    """Format a scan result as a JSON string.

    Args:
        result: The scan result to format.

    Returns:
        A JSON string with 2-space indentation.
    """
    return json.dumps(scan_result_to_dict(result), indent=2)


def inspect_to_dict(
    result: GitInspectResult | NonGitInspectResult,
) -> dict[str, object]:
    """Convert an inspect result to a plain dictionary for JSON serialization.

    The output uses a `kind` discriminator (`"git"` or `"non-git"`) so
    consumers can dispatch on shape.
    """
    if isinstance(result, GitInspectResult):
        return {
            "kind": "git",
            "path": str(result.path),
            "working_tree": {
                "clean": result.working_tree.clean,
                "staged": result.working_tree.staged,
                "modified": result.working_tree.modified,
                "untracked": result.working_tree.untracked,
            },
            "branches": {
                "total": result.branches.total,
                "no_upstream": result.branches.no_upstream,
                "ahead_of_upstream": result.branches.ahead_of_upstream,
            },
            "stash_count": result.stash_count,
            "last_commit_at": (
                result.last_commit_at.isoformat()
                if result.last_commit_at is not None
                else None
            ),
            "mtime": result.mtime.isoformat(),
            "remotes": [
                {
                    "name": r.name,
                    "url": r.url,
                    "host": r.host,
                    "owner": r.owner,
                    "repo": r.repo,
                }
                for r in result.remotes
            ],
            "scanned_at": result.scanned_at.isoformat(),
        }

    return {
        "kind": "non-git",
        "path": str(result.path),
        "file_count": result.file_count,
        "folder_count": result.folder_count,
        "total_size_bytes": result.total_size_bytes,
        "mtime": result.mtime.isoformat(),
        "scanned_at": result.scanned_at.isoformat(),
    }


def format_inspect_json(
    result: GitInspectResult | NonGitInspectResult,
) -> str:
    """Format an inspect result as a JSON string with 2-space indentation."""
    return json.dumps(inspect_to_dict(result), indent=2)
