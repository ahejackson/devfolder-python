"""Project classification logic for devfolder."""

from pathlib import Path

from .config import Config
from .git import get_git_remotes
from .models import Owner, ProjectNode, ProjectType

__all__ = [
    "classify_project",
    "get_git_remotes",
    "has_dot_git",
    "is_bare_git_repo",
    "is_empty_directory",
    "is_git_project",
    "match_owner",
    "parse_remote_url",
]


def parse_remote_url(url: str) -> tuple[str, str] | None:
    """Extract (host, owner) from a git remote URL.

    Handles SSH (`git@host:owner/repo.git`), HTTPS (`https://host/owner/repo.git`),
    and `git://` URLs.

    Args:
        url: The git remote URL.

    Returns:
        A `(host, owner)` tuple, or None if the URL can't be parsed.
    """
    if url.startswith("git@"):
        # git@github.com:owner/repo.git
        host_part, sep, path = url.partition(":")
        if not sep:
            return None
        host = host_part[len("git@") :]
    elif "://" in url:
        # https://github.com/owner/repo.git or git://github.com/owner/repo.git
        _, _, rest = url.partition("://")
        host, _, path = rest.partition("/")
    else:
        return None

    if not host:
        return None

    path_parts = [p for p in path.split("/") if p]
    if not path_parts:
        return None

    return host, path_parts[0]


def match_owner(url: str, owners: tuple[Owner, ...]) -> str | None:
    """Find the configured owner that matches the given remote URL.

    Matching is case-insensitive and requires both host and owner name to match.

    Args:
        url: The git remote URL.
        owners: The configured owners.

    Returns:
        The matched owner's name (preserving its configured casing),
        or None if no owner matches.
    """
    parsed = parse_remote_url(url)
    if parsed is None:
        return None

    host, url_owner = parsed
    for owner in owners:
        if (
            owner.host.lower() == host.lower()
            and owner.name.lower() == url_owner.lower()
        ):
            return owner.name

    return None


def is_empty_directory(path: Path) -> bool:
    """Check if a directory is empty (contains no files or subdirectories).

    Args:
        path: Path to check.

    Returns:
        True if the directory is empty.
    """
    try:
        return not any(path.iterdir())
    except OSError:
        return False


def has_dot_git(path: Path) -> bool:
    """Check if a path contains a `.git` entry (directory or file).

    A `.git` file (rather than directory) is used by git worktrees and
    submodules — it contains a `gitdir:` line pointing to the real
    git directory. Both layouts are valid git projects, so we accept
    either.

    Args:
        path: Path to check.

    Returns:
        True if `.git` exists at `path` as either a directory or a file.
    """
    dot_git = path / ".git"
    return dot_git.is_dir() or dot_git.is_file()


def is_bare_git_repo(path: Path) -> bool:
    """Check if a path looks structurally like a bare git repository.

    A bare repo has no working tree — the project directory itself
    holds the git data. Detected by the presence of `HEAD` (file),
    `objects/` (directory), and `refs/` (directory) at the top
    level. This is a fast structural check; the inspector confirms
    via `git rev-parse --is-bare-repository` when collecting full
    project detail.

    Args:
        path: Path to check.

    Returns:
        True if `path` appears to be a bare git repository.
    """
    return (
        (path / "HEAD").is_file()
        and (path / "objects").is_dir()
        and (path / "refs").is_dir()
    )


def is_git_project(path: Path) -> bool:
    """Check if a path is any recognised git project layout.

    Returns True for working-tree (`.git/` directory), linked (`.git`
    file — worktrees and submodules), and bare (`HEAD` + `objects/`
    + `refs/`) layouts. Used by the scanner to decide whether a
    directory is a project leaf or should be descended into as a
    category.

    Args:
        path: Path to check.

    Returns:
        True if any git layout is detected.
    """
    return has_dot_git(path) or is_bare_git_repo(path)


def classify_project(path: Path, config: Config) -> ProjectNode:
    """Classify a project based on its git status.

    Args:
        path: Path to the project directory.
        config: Configuration containing the owners list.

    Returns:
        A ProjectNode with the appropriate classification.
    """
    name = path.name

    # Non-git projects: empty or untracked.
    if not is_git_project(path):
        if is_empty_directory(path):
            return ProjectNode(
                name=name, path=path, project_type=ProjectType.EMPTY
            )
        return ProjectNode(
            name=name, path=path, project_type=ProjectType.LOCAL_UNTRACKED
        )

    # Git project (working-tree, linked, or bare). Classify by remotes.
    remotes = get_git_remotes(path)
    if not remotes:
        return ProjectNode(name=name, path=path, project_type=ProjectType.LOCAL_GIT)

    # Get the primary remote URL (origin first, then first available)
    if "origin" in remotes:
        remote_url = remotes["origin"]
    else:
        remote_url = next(iter(remotes.values()))

    # Check if this matches a configured owner
    matched = match_owner(remote_url, config.owners)
    if matched is not None:
        return ProjectNode(
            name=name,
            path=path,
            project_type=ProjectType.OWNED_REMOTE,
            remote_url=remote_url,
            owner=matched,
        )

    return ProjectNode(
        name=name,
        path=path,
        project_type=ProjectType.OTHER_REMOTE,
        remote_url=remote_url,
    )
