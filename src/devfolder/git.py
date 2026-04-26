"""Thin wrappers around the git CLI.

All functions here run `git` as a subprocess and parse the output. They
return sensible defaults on error (e.g. zero counts, None for missing
last-commit) rather than raising — callers don't need to distinguish
"git failed" from "no data" for the inspect/report use cases.
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

__all__ = [
    "BranchSummary",
    "WorkingTreeState",
    "branches",
    "get_git_remotes",
    "last_commit_at",
    "stash_count",
    "status",
]


@dataclass(frozen=True)
class WorkingTreeState:
    """Summary of `git status` output for a working tree."""

    clean: bool
    staged: int
    modified: int
    untracked: int


@dataclass(frozen=True)
class BranchSummary:
    """Summary of local branches and their upstream relationships."""

    total: int
    no_upstream: int
    ahead_of_upstream: int


def _run_git(path: Path, args: list[str]) -> tuple[int, str]:
    """Run a git subcommand in `path`. Returns (returncode, stdout).

    On OSError or SubprocessError, returns (-1, "").
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout
    except (OSError, subprocess.SubprocessError):
        return -1, ""


def get_git_remotes(path: Path) -> dict[str, str]:
    """Get all git remotes for a repository.

    Args:
        path: Path to the git repository.

    Returns:
        A dictionary mapping remote names to their URLs.
    """
    code, stdout = _run_git(path, ["remote", "-v"])
    if code != 0:
        return {}

    remotes: dict[str, str] = {}
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] not in remotes:
            # Only take the first occurrence (fetch, not push)
            remotes[parts[0]] = parts[1]

    return remotes


def status(path: Path) -> WorkingTreeState:
    """Summarise working tree state via `git status --porcelain=v1`.

    Each output line is `XY <path>`, where X is the staged status and Y
    is the working-tree status. `??` indicates untracked files.

    Args:
        path: Path to the git repository.

    Returns:
        A WorkingTreeState. On git failure returns a clean state with
        all counts at zero.
    """
    code, stdout = _run_git(path, ["status", "--porcelain=v1"])
    if code != 0:
        return WorkingTreeState(clean=True, staged=0, modified=0, untracked=0)

    staged = 0
    modified = 0
    untracked = 0
    for line in stdout.splitlines():
        if len(line) < 2:
            continue
        if line.startswith("??"):
            untracked += 1
            continue
        x, y = line[0], line[1]
        if x not in (" ", "?"):
            staged += 1
        if y not in (" ", "?"):
            modified += 1

    clean = staged == 0 and modified == 0 and untracked == 0
    return WorkingTreeState(
        clean=clean, staged=staged, modified=modified, untracked=untracked
    )


def branches(path: Path) -> BranchSummary:
    """Summarise local branches and their upstream tracking.

    Uses `git for-each-ref refs/heads/` with a custom format. The
    `upstream:track` field looks like `[ahead 3]`, `[behind 1]`,
    `[ahead 2, behind 1]`, or empty.

    Args:
        path: Path to the git repository.

    Returns:
        A BranchSummary. Empty-repo and git-failure cases yield
        all-zero counts.
    """
    fmt = "%(refname:short)|%(upstream:short)|%(upstream:track)"
    code, stdout = _run_git(
        path, ["for-each-ref", "refs/heads/", f"--format={fmt}"]
    )
    if code != 0:
        return BranchSummary(total=0, no_upstream=0, ahead_of_upstream=0)

    total = 0
    no_upstream = 0
    ahead = 0
    for line in stdout.splitlines():
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        _, upstream, track = parts
        total += 1
        if not upstream:
            no_upstream += 1
        if "ahead" in track:
            ahead += 1

    return BranchSummary(
        total=total, no_upstream=no_upstream, ahead_of_upstream=ahead
    )


def stash_count(path: Path) -> int:
    """Count stashes via `git stash list`. Zero if no stash exists."""
    code, stdout = _run_git(path, ["stash", "list"])
    if code != 0:
        return 0
    return sum(1 for line in stdout.splitlines() if line.strip())


def last_commit_at(path: Path) -> datetime | None:
    """Return the committer date of HEAD as a tz-aware datetime.

    Returns None for empty repos (no commits) or any git failure.
    """
    code, stdout = _run_git(path, ["log", "-1", "--format=%cI", "HEAD"])
    if code != 0:
        return None
    text = stdout.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
