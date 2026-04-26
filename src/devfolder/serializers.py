"""JSON serialization for devfolder scan results."""

import json

__all__ = ["format_json", "node_to_dict", "scan_result_to_dict"]

from .models import (
    CategoryNode,
    ErrorNode,
    IgnoredNode,
    Node,
    NodeKind,
    ProjectNode,
    ScanResult,
    SymlinkNode,
)


def node_to_dict(node: Node) -> dict[str, object]:
    """Convert a node to a plain dictionary for JSON serialization.

    Args:
        node: The node to convert.

    Returns:
        A dictionary representation of the node.
    """
    match node.kind:
        case NodeKind.PROJECT:
            assert isinstance(node, ProjectNode)
            return {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "project_type": node.project_type.value,
                "remote_url": node.remote_url,
                "owner": node.owner,
            }

        case NodeKind.CATEGORY:
            assert isinstance(node, CategoryNode)
            return {
                "kind": node.kind.value,
                "name": node.name,
                "path": str(node.path),
                "is_empty": node.is_empty,
                "children": [node_to_dict(child) for child in node.children],
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


def scan_result_to_dict(result: ScanResult) -> dict[str, object]:
    """Convert a scan result to a plain dictionary for JSON serialization.

    Args:
        result: The scan result to convert.

    Returns:
        A dictionary representation of the scan result.
    """
    root_project: dict[str, object] | None = None
    if result.root_project is not None:
        root_project = node_to_dict(result.root_project)

    return {
        "generated_at": result.generated_at.isoformat(),
        "root": str(result.root),
        "is_root_project": result.is_root_project,
        "root_project": root_project,
        "children": [node_to_dict(child) for child in result.children],
    }


def format_json(result: ScanResult) -> str:
    """Format a scan result as a JSON string.

    Args:
        result: The scan result to format.

    Returns:
        A JSON string with 2-space indentation.
    """
    return json.dumps(scan_result_to_dict(result), indent=2)
