"""Output formatting for devfolder."""

__all__ = ["format_tree"]

from .models import (
    CategoryNode,
    ErrorNode,
    IgnoredNode,
    IgnoreReason,
    Node,
    NodeKind,
    ProjectNode,
    ProjectType,
    ScanResult,
    SymlinkNode,
)

# Box-drawing characters for tree
PIPE = "│"
TEE = "├"
ELBOW = "└"
DASH = "──"


def format_project_type(project_type: ProjectType) -> str:
    """Format a project type for display.

    Args:
        project_type: The project type to format.

    Returns:
        A formatted string for the project type.
    """
    return f"[{project_type.value}]"


def format_ignore_reason(reason: IgnoreReason) -> str:
    """Format an ignore reason for display.

    Args:
        reason: The ignore reason to format.

    Returns:
        A formatted string for the ignore reason.
    """
    match reason:
        case IgnoreReason.DOTFOLDER:
            return "[ignored: dotfolder]"
        case IgnoreReason.NODE_MODULES:
            return "[ignored: node_modules]"
        case _:
            raise ValueError(f"Unknown ignore reason: {reason}")


def format_node(node: Node, prefix: str = "", is_last: bool = True) -> list[str]:
    """Format a node for tree display.

    Args:
        node: The node to format.
        prefix: The prefix for indentation.
        is_last: Whether this is the last child in its parent.

    Returns:
        A list of formatted lines.
    """
    lines: list[str] = []
    connector = ELBOW if is_last else TEE
    child_prefix = prefix + ("    " if is_last else f"{PIPE}   ")

    match node.kind:
        case NodeKind.PROJECT:
            assert isinstance(node, ProjectNode)
            type_str = format_project_type(node.project_type)
            remote_str = f" {node.remote_url}" if node.remote_url else ""
            line = f"{prefix}{connector}{DASH} {node.name}/ {type_str}{remote_str}"
            lines.append(line)

        case NodeKind.CATEGORY:
            assert isinstance(node, CategoryNode)
            empty_str = " [empty]" if node.is_empty else ""
            lines.append(f"{prefix}{connector}{DASH} {node.name}/{empty_str}")

            # Format children
            for i, child in enumerate(node.children):
                is_child_last = i == len(node.children) - 1
                lines.extend(format_node(child, child_prefix, is_child_last))

        case NodeKind.SYMLINK:
            assert isinstance(node, SymlinkNode)
            target_str = f" -> {node.target}" if node.target else ""
            line = f"{prefix}{connector}{DASH} {node.name}/{target_str} [symlink]"
            lines.append(line)

        case NodeKind.IGNORED:
            assert isinstance(node, IgnoredNode)
            reason_str = format_ignore_reason(node.reason)
            lines.append(f"{prefix}{connector}{DASH} {node.name}/ {reason_str}")

        case NodeKind.ERROR:
            assert isinstance(node, ErrorNode)
            lines.append(
                f"{prefix}{connector}{DASH} {node.name}/ [error: {node.error_message}]"
            )

    return lines


def format_tree(result: ScanResult) -> str:
    """Format a scan result as a tree.

    Args:
        result: The scan result to format.

    Returns:
        A formatted tree string.
    """
    lines: list[str] = []

    # Root line
    if result.is_root_project:
        assert result.root_project is not None
        type_str = format_project_type(result.root_project.project_type)
        remote_str = (
            f" {result.root_project.remote_url}"
            if result.root_project.remote_url
            else ""
        )
        lines.append(f"{result.root}/ {type_str}{remote_str}")
    else:
        lines.append(f"{result.root}/")

    # Format children
    for i, child in enumerate(result.children):
        is_last = i == len(result.children) - 1
        lines.extend(format_node(child, "", is_last))

    return "\n".join(lines)
