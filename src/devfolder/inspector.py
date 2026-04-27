"""Per-project inspect logic.

`inspect(path)` dispatches on the structural git layout (working-tree,
linked, bare, or none) and returns one of `GitInspectResult`,
`BareGitInspectResult`, or `NonGitInspectResult`. Designed for the
"salvage data" use case: surface unpushed work, untracked branches,
disk usage, and last-modified signals so a human can decide whether
a project needs attention.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from .classifier import detect_git_layout
from .git import (
    GitMeta,
    branches,
    get_git_remotes,
    git_meta,
    last_commit_at,
    parse_remote,
    stash_count,
    status,
)
from .models import (
    BareGitInspectResult,
    GitInspectResult,
    GitLayout,
    LinkedRepo,
    LinkedRepoKind,
    NonGitInspectResult,
)

__all__ = ["EXCLUDED_WALK_DIRS", "inspect"]


# Directories skipped when walking non-git projects to compute file/folder
# counts and total size. These are universally noisy: large, fast-changing,
# regenerable, and uninformative for the salvage use case. Add to this set
# only when the noise is truly universal — project-specific build outputs
# (`dist`, `target`, `__pycache__`, etc.) are intentionally walked.
EXCLUDED_WALK_DIRS = frozenset({"node_modules", ".git", ".venv"})


def inspect(
    path: Path,
) -> GitInspectResult | BareGitInspectResult | NonGitInspectResult:
    """Inspect a single project directory.

    Args:
        path: Directory to inspect. Should already exist and be a directory;
            callers (CLI) are responsible for validation.

    Returns:
        A GitInspectResult for working-tree git projects (including
        worktrees and submodules), a BareGitInspectResult for bare
        repos, or a NonGitInspectResult for empty/untracked dirs.
    """
    scanned_at = datetime.now(UTC)
    mtime = _mtime(path)

    layout = detect_git_layout(path)
    if layout is None:
        return _inspect_non_git(path, mtime=mtime, scanned_at=scanned_at)

    meta = git_meta(path)
    is_bare = _resolve_bare(path, layout=layout, meta=meta)

    if is_bare:
        return _inspect_bare_git(path, mtime=mtime, scanned_at=scanned_at)
    return _inspect_git(path, meta=meta, mtime=mtime, scanned_at=scanned_at)


def _resolve_bare(
    path: Path, *, layout: GitLayout, meta: GitMeta | None
) -> bool:
    """Decide whether to treat the project as bare.

    Trusts `git rev-parse` when available. If structural detection
    and git disagree, emits a stderr warning and trusts git. When
    git is unavailable, falls back to the structural classification.
    """
    structural_bare = layout is GitLayout.BARE
    if meta is None:
        return structural_bare

    if meta.is_bare != structural_bare:
        verdict = "bare" if meta.is_bare else "non-bare"
        seen = "bare" if structural_bare else "non-bare"
        print(
            f"warning: structural detection said {seen} but git says "
            f"{verdict} for {path}; trusting git",
            file=sys.stderr,
        )
    return meta.is_bare


def _inspect_git(
    path: Path,
    *,
    meta: GitMeta | None,
    mtime: datetime,
    scanned_at: datetime,
) -> GitInspectResult:
    """Collect inspect data for a working-tree git project."""
    remotes_raw = get_git_remotes(path)
    remotes = tuple(
        parse_remote(name, url) for name, url in sorted(remotes_raw.items())
    )

    if meta is not None:
        gitdir = meta.gitdir
        linked_to = _derive_linked_to(meta)
    else:
        # `git rev-parse` failed — fall back to a best-effort gitdir
        # path and skip linkage info. The structural detection got us
        # here, so `.git` should exist as a file or directory.
        gitdir = path / ".git"
        linked_to = None

    return GitInspectResult(
        path=path,
        gitdir=gitdir,
        linked_to=linked_to,
        working_tree=status(path),
        branches=branches(path),
        stash_count=stash_count(path),
        last_commit_at=last_commit_at(path),
        mtime=mtime,
        remotes=remotes,
        scanned_at=scanned_at,
    )


def _inspect_bare_git(
    path: Path, *, mtime: datetime, scanned_at: datetime
) -> BareGitInspectResult:
    """Collect inspect data for a bare git repository."""
    remotes_raw = get_git_remotes(path)
    remotes = tuple(
        parse_remote(name, url) for name, url in sorted(remotes_raw.items())
    )
    return BareGitInspectResult(
        path=path,
        branches=branches(path),
        stash_count=stash_count(path),
        last_commit_at=last_commit_at(path),
        mtime=mtime,
        remotes=remotes,
        scanned_at=scanned_at,
    )


def _derive_linked_to(meta: GitMeta) -> LinkedRepo | None:
    """Derive linkage info from a `GitMeta`.

    Submodules are identified by a non-empty superproject path
    (returned by `git rev-parse --show-superproject-working-tree`).
    Worktrees are identified by `gitdir != common_dir` — the common
    dir is the main repo's gitdir, and the main repo's working tree
    is its parent.
    """
    if meta.superproject_path is not None:
        return LinkedRepo(
            kind=LinkedRepoKind.SUBMODULE,
            linked_repo_path=meta.superproject_path,
        )
    if meta.gitdir != meta.common_dir:
        return LinkedRepo(
            kind=LinkedRepoKind.WORKTREE,
            linked_repo_path=meta.common_dir.parent,
        )
    return None


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
