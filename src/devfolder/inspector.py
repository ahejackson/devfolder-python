"""Per-project inspect logic.

`inspect(path)` dispatches on whether the path looks like a git
project (has a `.git` directory) and returns either a
`GitInspectResult` or a `NonGitInspectResult`. Designed for the
"salvage data" use case: surface unpushed work, untracked branches,
disk usage, and last-modified signals so a human can decide whether
a project needs attention.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

from .classifier import has_git_directory
from .git import (
    branches,
    get_git_remotes,
    last_commit_at,
    parse_remote,
    stash_count,
    status,
)
from .models import GitInspectResult, NonGitInspectResult

__all__ = ["EXCLUDED_WALK_DIRS", "inspect"]


# Directories skipped when walking non-git projects to compute file/folder
# counts and total size. These are universally noisy: large, fast-changing,
# regenerable, and uninformative for the salvage use case. Add to this set
# only when the noise is truly universal — project-specific build outputs
# (`dist`, `target`, `__pycache__`, etc.) are intentionally walked.
EXCLUDED_WALK_DIRS = frozenset({"node_modules", ".git", ".venv"})


def inspect(path: Path) -> GitInspectResult | NonGitInspectResult:
    """Inspect a single project directory.

    Args:
        path: Directory to inspect. Should already exist and be a directory;
            callers (CLI) are responsible for validation.

    Returns:
        A GitInspectResult if `path` contains `.git/`, otherwise a
        NonGitInspectResult.
    """
    scanned_at = datetime.now(UTC)
    mtime = _mtime(path)

    if has_git_directory(path):
        return _inspect_git(path, mtime=mtime, scanned_at=scanned_at)
    return _inspect_non_git(path, mtime=mtime, scanned_at=scanned_at)


def _inspect_git(
    path: Path, *, mtime: datetime, scanned_at: datetime
) -> GitInspectResult:
    """Collect git-project inspect data."""
    remotes_raw = get_git_remotes(path)
    remotes = tuple(
        parse_remote(name, url) for name, url in sorted(remotes_raw.items())
    )
    return GitInspectResult(
        path=path,
        working_tree=status(path),
        branches=branches(path),
        stash_count=stash_count(path),
        last_commit_at=last_commit_at(path),
        mtime=mtime,
        remotes=remotes,
        scanned_at=scanned_at,
    )


def _inspect_non_git(
    path: Path, *, mtime: datetime, scanned_at: datetime
) -> NonGitInspectResult:
    """Walk a non-git project to collect file/folder counts and size."""
    file_count, folder_count, total_size = _walk_counts(path)
    return NonGitInspectResult(
        path=path,
        file_count=file_count,
        folder_count=folder_count,
        total_size_bytes=total_size,
        mtime=mtime,
        scanned_at=scanned_at,
    )


def _mtime(path: Path) -> datetime:
    """Return the directory's mtime as a tz-aware UTC datetime."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def _walk_counts(path: Path) -> tuple[int, int, int]:
    """Walk `path` and return (file_count, folder_count, total_size_bytes).

    Symlinks are not followed and not counted. EXCLUDED_WALK_DIRS are
    skipped entirely.
    """
    file_count = 0
    folder_count = 0
    total_size = 0
    root_str = str(path)

    for current, dirs, files in os.walk(path, followlinks=False):
        # Filter excluded names and symlinked subdirs in-place so os.walk
        # doesn't descend into them.
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDED_WALK_DIRS
            and not (Path(current) / d).is_symlink()
        ]

        # Count this directory unless it's the root.
        if current != root_str:
            folder_count += 1

        for fname in files:
            fp = Path(current) / fname
            if fp.is_symlink():
                continue
            try:
                total_size += fp.stat().st_size
            except OSError:
                continue
            file_count += 1

    return file_count, folder_count, total_size
