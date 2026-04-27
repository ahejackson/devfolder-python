"""Output formatting for devfolder."""

from datetime import UTC, datetime

__all__ = ["format_inspect_text", "format_tree"]

from .models import (
    BareGitInspectResult,
    BranchSummary,
    CategoryNode,
    ErrorNode,
    GitInspectResult,
    IgnoredNode,
    IgnoreReason,
    Node,
    NodeKind,
    NonGitInspectResult,
    ProjectNode,
    ProjectType,
    RemoteRecord,
    ScanResult,
    SymlinkNode,
)

# Box-drawing characters for tree
PIPE = "│"
TEE = "├"
ELBOW = "└"
DASH = "──"


def format_project_type(project_type: ProjectType, owner: str | None = None) -> str:
    """Format a project type for display.

    Args:
        project_type: The project type to format.
        owner: The matched owner name, shown inline for OWNED_REMOTE projects.

    Returns:
        A formatted string for the project type.
    """
    if project_type is ProjectType.OWNED_REMOTE and owner is not None:
        return f"[{project_type.value}: {owner}]"
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
            type_str = format_project_type(node.project_type, node.owner)
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
        type_str = format_project_type(
            result.root_project.project_type, result.root_project.owner
        )
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


def format_inspect_text(
    result: GitInspectResult | BareGitInspectResult | NonGitInspectResult,
) -> str:
    """Format an inspect result as a human-readable text block."""
    if isinstance(result, GitInspectResult):
        return _format_git_inspect_text(result)
    if isinstance(result, BareGitInspectResult):
        return _format_bare_git_inspect_text(result)
    return _format_non_git_inspect_text(result)


def _format_git_inspect_text(result: GitInspectResult) -> str:
    wt = result.working_tree
    if wt.clean:
        wt_line = "clean"
    else:
        parts = []
        if wt.staged:
            parts.append(f"{wt.staged} staged")
        if wt.modified:
            parts.append(f"{wt.modified} modified")
        if wt.untracked:
            parts.append(f"{wt.untracked} untracked")
        wt_line = "dirty (" + ", ".join(parts) + ")"

    branches_line = _format_branches(result.branches)

    last_commit_line = (
        _format_datetime(result.last_commit_at)
        if result.last_commit_at is not None
        else "(no commits)"
    )

    lines = [
        f"{result.path} (git)",
        "",
        f"Working tree:   {wt_line}",
        f"Branches:       {branches_line}",
        f"Stash:          {result.stash_count}",
        f"Last commit:    {last_commit_line}",
        f"Last modified:  {_format_datetime(result.mtime)}",
    ]

    if result.linked_to is not None:
        lines.append(
            f"Linked to:      {result.linked_to.kind.value} of "
            f"{result.linked_to.linked_repo_path}"
        )

    lines.extend(_format_remotes_block(result.remotes))

    lines.append("")
    lines.append(f"Scanned at:     {result.scanned_at.isoformat()}")
    return "\n".join(lines)


def _format_bare_git_inspect_text(result: BareGitInspectResult) -> str:
    branches_line = _format_branches(result.branches)
    last_commit_line = (
        _format_datetime(result.last_commit_at)
        if result.last_commit_at is not None
        else "(no commits)"
    )

    lines = [
        f"{result.path} (bare git)",
        "",
        f"Branches:       {branches_line}",
        f"Stash:          {result.stash_count}",
        f"Last commit:    {last_commit_line}",
        f"Last modified:  {_format_datetime(result.mtime)}",
    ]

    lines.extend(_format_remotes_block(result.remotes))

    lines.append("")
    lines.append(f"Scanned at:     {result.scanned_at.isoformat()}")
    return "\n".join(lines)


def _format_branches(branches: BranchSummary) -> str:
    return (
        f"{branches.total} total · "
        f"{branches.no_upstream} without upstream · "
        f"{branches.ahead_of_upstream} ahead"
    )


def _format_remotes_block(remotes: tuple[RemoteRecord, ...]) -> list[str]:
    lines: list[str] = []
    if remotes:
        lines.append("")
        lines.append("Remotes:")
        for r in remotes:
            location = (
                f"{r.host}/{r.owner}/{r.repo}"
                if r.host and r.owner and r.repo
                else "(unparseable)"
            )
            lines.append(f"  {r.name:8} {location}  ({r.url})")
    else:
        lines.append("")
        lines.append("Remotes:        (none)")
    return lines


def _format_non_git_inspect_text(result: NonGitInspectResult) -> str:
    return "\n".join(
        [
            f"{result.path} (non-git)",
            "",
            f"Files:          {result.file_count}",
            f"Folders:        {result.folder_count}",
            f"Size on disk:   {_format_bytes(result.total_size_bytes)}",
            f"Last modified:  {_format_datetime(result.mtime)}",
            "",
            f"Scanned at:     {result.scanned_at.isoformat()}",
        ]
    )


def _format_datetime(dt: datetime) -> str:
    """Format a tz-aware datetime as `YYYY-MM-DD HH:MM:SS UTC`."""
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_bytes(n: int) -> str:
    """Format a byte count as a human-readable string (B, KB, MB, GB, TB)."""
    if n < 1024:
        return f"{n} B"
    size = float(n)
    for unit in ("KB", "MB", "GB"):
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    size /= 1024
    return f"{size:.1f} TB"
