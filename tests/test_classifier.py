"""Tests for devfolder.classifier module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devfolder.classifier import (
    classify_project,
    get_git_remotes,
    has_git_directory,
    is_empty_directory,
    username_in_remote_url,
)
from devfolder.config import Config
from devfolder.models import ProjectType

from .conftest import make_remote_patch

# --- username_in_remote_url ---


class TestUsernameInRemoteUrl:
    """Tests for username matching across URL formats."""

    @pytest.mark.parametrize(
        ("url", "username", "expected"),
        [
            # SSH format
            ("git@github.com:testuser/repo.git", "testuser", True),
            ("git@github.com:otheruser/repo.git", "testuser", False),
            ("git@gitlab.com:testuser/repo.git", "testuser", True),
            # HTTPS format
            ("https://github.com/testuser/repo.git", "testuser", True),
            ("https://github.com/otheruser/repo.git", "testuser", False),
            ("https://gitlab.com/testuser/repo.git", "testuser", True),
            # git:// format
            ("git://github.com/testuser/repo.git", "testuser", True),
            ("git://github.com/otheruser/repo.git", "testuser", False),
            # Case insensitive
            ("git@github.com:TestUser/repo.git", "testuser", True),
            ("https://github.com/TESTUSER/repo.git", "testuser", True),
            # Partial matches should not match
            ("git@github.com:testuser2/repo.git", "testuser", False),
            ("https://github.com/nottestuser/repo.git", "testuser", False),
        ],
        ids=[
            "ssh-match",
            "ssh-no-match",
            "ssh-gitlab",
            "https-match",
            "https-no-match",
            "https-gitlab",
            "git-proto-match",
            "git-proto-no-match",
            "ssh-case-insensitive",
            "https-case-insensitive",
            "ssh-partial-no-match",
            "https-partial-no-match",
        ],
    )
    def test_url_matching(
        self, url: str, username: str, expected: bool
    ) -> None:
        assert username_in_remote_url(url, username) is expected


# --- is_empty_directory ---


class TestIsEmptyDirectory:
    """Tests for empty directory detection."""

    def test_empty_directory(self, empty_dir: Path) -> None:
        assert is_empty_directory(empty_dir) is True

    def test_non_empty_directory(self, untracked_project: Path) -> None:
        assert is_empty_directory(untracked_project) is False

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        assert is_empty_directory(missing) is False


# --- has_git_directory ---


class TestHasGitDirectory:
    """Tests for .git directory detection."""

    def test_has_git(self, local_git_project: Path) -> None:
        assert has_git_directory(local_git_project) is True

    def test_no_git(self, untracked_project: Path) -> None:
        assert has_git_directory(untracked_project) is False

    def test_empty_directory(self, empty_dir: Path) -> None:
        assert has_git_directory(empty_dir) is False

    def test_git_file_not_dir(self, tmp_path: Path) -> None:
        """A .git file (not directory) should not count."""
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").write_text("gitdir: /elsewhere")
        assert has_git_directory(project) is False


# --- classify_project ---


class TestClassifyProject:
    """Tests for project classification."""

    def test_empty_project(
        self, empty_dir: Path, config: Config
    ) -> None:
        result = classify_project(empty_dir, config)
        assert result.project_type is ProjectType.EMPTY
        assert result.remote_url is None
        assert result.name == "empty-project"

    def test_untracked_project(
        self, untracked_project: Path, config: Config
    ) -> None:
        result = classify_project(untracked_project, config)
        assert result.project_type is ProjectType.LOCAL_UNTRACKED
        assert result.remote_url is None

    def test_local_git_project(
        self, local_git_project: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = classify_project(local_git_project, config)
        assert result.project_type is ProjectType.LOCAL_GIT
        assert result.remote_url is None

    def test_personal_remote_project(
        self, personal_remote_project: Path, config: Config
    ) -> None:
        remotes = {"origin": "git@github.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(personal_remote_project, config)
        assert result.project_type is ProjectType.PERSONAL_REMOTE
        assert result.remote_url == "git@github.com:testuser/repo.git"

    def test_other_remote_project(
        self, other_remote_project: Path, config: Config
    ) -> None:
        remotes = {"origin": "git@github.com:someone/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(other_remote_project, config)
        assert result.project_type is ProjectType.OTHER_REMOTE
        assert result.remote_url == "git@github.com:someone/repo.git"

    def test_no_username_configured(
        self,
        personal_remote_project: Path,
        config_no_username: Config,
    ) -> None:
        """With no username in config, all remote projects are 'other'."""
        remotes = {"origin": "git@github.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(
                personal_remote_project, config_no_username
            )
        assert result.project_type is ProjectType.OTHER_REMOTE

    def test_origin_preferred_over_other_remotes(
        self, personal_remote_project: Path, config: Config
    ) -> None:
        """When origin exists, it should be used for classification."""
        remotes = {
            "upstream": "git@github.com:someone/repo.git",
            "origin": "git@github.com:testuser/repo.git",
        }
        with make_remote_patch(remotes):
            result = classify_project(personal_remote_project, config)
        assert result.project_type is ProjectType.PERSONAL_REMOTE
        assert result.remote_url == "git@github.com:testuser/repo.git"

    def test_fallback_to_first_remote_when_no_origin(
        self, personal_remote_project: Path, config: Config
    ) -> None:
        """When no origin, use the first available remote."""
        remotes = {"upstream": "git@github.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(personal_remote_project, config)
        assert result.project_type is ProjectType.PERSONAL_REMOTE

    def test_project_path_preserved(
        self, empty_dir: Path, config: Config
    ) -> None:
        result = classify_project(empty_dir, config)
        assert result.path == empty_dir


# --- get_git_remotes ---


class TestGetGitRemotes:
    """Tests for git remote parsing."""

    def _mock_run(self, stdout: str, returncode: int = 0) -> MagicMock:
        """Create a mock for subprocess.run.

        Args:
            stdout: The stdout content to return.
            returncode: The return code to simulate.

        Returns:
            A configured MagicMock.
        """
        mock_result = MagicMock()
        mock_result.stdout = stdout
        mock_result.returncode = returncode
        return mock_result

    def test_single_remote(self, tmp_path: Path) -> None:
        stdout = (
            "origin\tgit@github.com:user/repo.git (fetch)\n"
            "origin\tgit@github.com:user/repo.git (push)\n"
        )
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {"origin": "git@github.com:user/repo.git"}

    def test_multiple_remotes(self, tmp_path: Path) -> None:
        stdout = (
            "origin\tgit@github.com:user/repo.git (fetch)\n"
            "origin\tgit@github.com:user/repo.git (push)\n"
            "upstream\thttps://github.com/org/repo.git (fetch)\n"
            "upstream\thttps://github.com/org/repo.git (push)\n"
        )
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {
            "origin": "git@github.com:user/repo.git",
            "upstream": "https://github.com/org/repo.git",
        }

    def test_prefers_fetch_over_push(self, tmp_path: Path) -> None:
        """When fetch and push URLs differ, use the fetch URL."""
        stdout = (
            "origin\tgit@github.com:user/repo.git (fetch)\n"
            "origin\tgit@github.com:user/repo-push.git (push)\n"
        )
        with patch("subprocess.run", return_value=self._mock_run(stdout)):
            remotes = get_git_remotes(tmp_path)

        assert remotes["origin"] == "git@github.com:user/repo.git"

    def test_empty_output(self, tmp_path: Path) -> None:
        with patch("subprocess.run", return_value=self._mock_run("")):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}

    def test_nonzero_return_code(self, tmp_path: Path) -> None:
        mock = self._mock_run("", returncode=128)
        with patch("subprocess.run", return_value=mock):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}

    def test_subprocess_error(self, tmp_path: Path) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("git not found"),
        ):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}

    def test_os_error(self, tmp_path: Path) -> None:
        with patch(
            "subprocess.run",
            side_effect=OSError("no such file"),
        ):
            remotes = get_git_remotes(tmp_path)

        assert remotes == {}
