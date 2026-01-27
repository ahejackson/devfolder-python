"""Project classification logic for devfolder."""

import subprocess
from pathlib import Path

from .config import Config
from .models import ProjectNode, ProjectType


def get_git_remotes(path: Path) -> dict[str, str]:
    """Get all git remotes for a repository.

    Args:
        path: Path to the git repository.

    Returns:
        A dictionary mapping remote names to their URLs.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return {}

        remotes: dict[str, str] = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] not in remotes:
                # Only take the first occurrence (fetch, not push)
                remotes[parts[0]] = parts[1]

        return remotes
    except (OSError, subprocess.SubprocessError):
        return {}


def username_in_remote_url(url: str, username: str) -> bool:
    """Check if a username appears in a git remote URL.

    Handles various URL formats:
    - git@github.com:username/repo.git
    - https://github.com/username/repo.git
    - git://github.com/username/repo.git

    Args:
        url: The git remote URL.
        username: The username to look for.

    Returns:
        True if the username is found in the URL's path component.
    """
    # Normalize the URL to extract the path
    if url.startswith("git@"):
        # git@github.com:username/repo.git -> username/repo.git
        _, _, path = url.partition(":")
    elif "://" in url:
        # https://github.com/username/repo.git -> /username/repo.git
        _, _, rest = url.partition("://")
        _, _, path = rest.partition("/")
        path = "/" + path
    else:
        path = url

    # Check if username appears as first path component
    path_parts = [p for p in path.split("/") if p]
    if path_parts and path_parts[0].lower() == username.lower():
        return True

    return False


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


def has_git_directory(path: Path) -> bool:
    """Check if a path contains a .git directory.

    Args:
        path: Path to check.

    Returns:
        True if the path has a .git subdirectory.
    """
    return (path / ".git").is_dir()


def classify_project(path: Path, config: Config) -> ProjectNode:
    """Classify a project based on its git status.

    Args:
        path: Path to the project directory.
        config: Configuration containing the username.

    Returns:
        A ProjectNode with the appropriate classification.
    """
    name = path.name

    # Check if empty
    if is_empty_directory(path):
        return ProjectNode(name=name, path=path, project_type=ProjectType.EMPTY)

    # Check if it's a git repository
    if not has_git_directory(path):
        return ProjectNode(
            name=name, path=path, project_type=ProjectType.LOCAL_UNTRACKED
        )

    # Get remotes
    remotes = get_git_remotes(path)
    if not remotes:
        return ProjectNode(name=name, path=path, project_type=ProjectType.LOCAL_GIT)

    # Get the primary remote URL (origin first, then first available)
    remote_url = remotes.get("origin") or next(iter(remotes.values()))

    # Check if it's a personal remote
    if config.username and username_in_remote_url(remote_url, config.username):
        return ProjectNode(
            name=name,
            path=path,
            project_type=ProjectType.PERSONAL_REMOTE,
            remote_url=remote_url,
        )

    return ProjectNode(
        name=name,
        path=path,
        project_type=ProjectType.OTHER_REMOTE,
        remote_url=remote_url,
    )
