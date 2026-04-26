"""Tests for devfolder.classifier module."""

from pathlib import Path

import pytest

from devfolder.classifier import (
    classify_project,
    has_git_directory,
    is_empty_directory,
    match_owner,
    parse_remote_url,
)
from devfolder.config import Config
from devfolder.models import Owner, ProjectType

from .conftest import make_remote_patch

# --- parse_remote_url ---


class TestParseRemoteUrl:
    """Tests for URL parsing across formats."""

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            # SSH
            ("git@github.com:owner/repo.git", ("github.com", "owner")),
            ("git@gitlab.com:owner/repo.git", ("gitlab.com", "owner")),
            ("git@github.com:org-name/some-repo.git", ("github.com", "org-name")),
            # HTTPS
            ("https://github.com/owner/repo.git", ("github.com", "owner")),
            ("https://gitlab.com/owner/repo.git", ("gitlab.com", "owner")),
            ("http://example.com/owner/repo", ("example.com", "owner")),
            # git://
            ("git://github.com/owner/repo.git", ("github.com", "owner")),
            # Trailing slash variations
            ("https://github.com/owner/repo", ("github.com", "owner")),
        ],
        ids=[
            "ssh-github",
            "ssh-gitlab",
            "ssh-org-name",
            "https-github",
            "https-gitlab",
            "http-plain",
            "git-proto",
            "https-no-suffix",
        ],
    )
    def test_parses_valid_urls(
        self, url: str, expected: tuple[str, str]
    ) -> None:
        assert parse_remote_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "not-a-url",
            "git@",
            "https://",
            "https://github.com",
            "https://github.com/",
            "git@github.com",
        ],
        ids=[
            "empty",
            "no-scheme",
            "ssh-no-host",
            "https-no-host",
            "https-host-only",
            "https-host-trailing-slash",
            "ssh-no-path",
        ],
    )
    def test_rejects_invalid_urls(self, url: str) -> None:
        assert parse_remote_url(url) is None


# --- match_owner ---


class TestMatchOwner:
    """Tests for owner matching against URLs."""

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            # Personal account on GitHub — matches.
            ("git@github.com:me/repo.git", "me"),
            ("https://github.com/me/repo.git", "me"),
            ("git://github.com/me/repo.git", "me"),
            # GitHub org — matches.
            ("git@github.com:my-org/repo.git", "my-org"),
            ("https://github.com/my-org/repo.git", "my-org"),
            # GitLab account — matches.
            ("git@gitlab.com:old-me/repo.git", "old-me"),
            ("https://gitlab.com/old-me/repo.git", "old-me"),
            # Case insensitive.
            ("git@github.com:ME/repo.git", "me"),
            ("https://GITHUB.COM/me/repo.git", "me"),
        ],
        ids=[
            "ssh-personal-github",
            "https-personal-github",
            "git-proto-personal-github",
            "ssh-org-github",
            "https-org-github",
            "ssh-gitlab",
            "https-gitlab",
            "ssh-case-insensitive-name",
            "https-case-insensitive-host",
        ],
    )
    def test_matches(self, url: str, expected: str) -> None:
        owners = (
            Owner(name="me", host="github.com"),
            Owner(name="my-org", host="github.com"),
            Owner(name="old-me", host="gitlab.com"),
        )
        assert match_owner(url, owners) == expected

    @pytest.mark.parametrize(
        "url",
        [
            # Right name, wrong host.
            "git@gitlab.com:me/repo.git",
            "https://gitlab.com/me/repo.git",
            # Right host, wrong name.
            "git@github.com:somebody-else/repo.git",
            "https://github.com/somebody-else/repo.git",
            # Wrong host AND wrong name.
            "git@bitbucket.org:somebody/repo.git",
            # Partial-name false positive guard.
            "git@github.com:me-too/repo.git",
            "https://github.com/not-me/repo.git",
        ],
        ids=[
            "ssh-name-wrong-host",
            "https-name-wrong-host",
            "ssh-host-wrong-name",
            "https-host-wrong-name",
            "ssh-both-wrong",
            "ssh-partial-prefix",
            "https-partial-suffix",
        ],
    )
    def test_no_match(self, url: str) -> None:
        owners = (
            Owner(name="me", host="github.com"),
            Owner(name="old-me", host="gitlab.com"),
        )
        assert match_owner(url, owners) is None

    def test_empty_owners_never_matches(self) -> None:
        assert match_owner("git@github.com:me/repo.git", ()) is None

    def test_unparseable_url_returns_none(self) -> None:
        owners = (Owner(name="me", host="github.com"),)
        assert match_owner("not-a-url", owners) is None

    def test_returns_configured_casing(self) -> None:
        """The returned name uses the casing from config, not the URL."""
        owners = (Owner(name="MyOrg", host="github.com"),)
        assert match_owner("git@github.com:myorg/repo.git", owners) == "MyOrg"


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
        assert result.owner is None
        assert result.name == "empty-project"

    def test_untracked_project(
        self, untracked_project: Path, config: Config
    ) -> None:
        result = classify_project(untracked_project, config)
        assert result.project_type is ProjectType.LOCAL_UNTRACKED
        assert result.remote_url is None
        assert result.owner is None

    def test_local_git_project(
        self, local_git_project: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = classify_project(local_git_project, config)
        assert result.project_type is ProjectType.LOCAL_GIT
        assert result.remote_url is None
        assert result.owner is None

    def test_owned_remote_project(
        self, owned_remote_project: Path, config: Config
    ) -> None:
        remotes = {"origin": "git@github.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(owned_remote_project, config)
        assert result.project_type is ProjectType.OWNED_REMOTE
        assert result.remote_url == "git@github.com:testuser/repo.git"
        assert result.owner == "testuser"

    def test_other_remote_project(
        self, other_remote_project: Path, config: Config
    ) -> None:
        remotes = {"origin": "git@github.com:someone/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(other_remote_project, config)
        assert result.project_type is ProjectType.OTHER_REMOTE
        assert result.remote_url == "git@github.com:someone/repo.git"
        assert result.owner is None

    def test_no_owners_configured(
        self,
        owned_remote_project: Path,
        config_no_owners: Config,
    ) -> None:
        """With no owners in config, all remote projects are 'other'."""
        remotes = {"origin": "git@github.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(
                owned_remote_project, config_no_owners
            )
        assert result.project_type is ProjectType.OTHER_REMOTE
        assert result.owner is None

    def test_matching_name_wrong_host_is_other_remote(
        self, owned_remote_project: Path, config: Config
    ) -> None:
        """A matching owner name on the wrong host doesn't classify as owned."""
        remotes = {"origin": "git@gitlab.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(owned_remote_project, config)
        assert result.project_type is ProjectType.OTHER_REMOTE
        assert result.owner is None

    def test_origin_preferred_over_other_remotes(
        self, owned_remote_project: Path, config: Config
    ) -> None:
        """When origin exists, it should be used for classification."""
        remotes = {
            "upstream": "git@github.com:someone/repo.git",
            "origin": "git@github.com:testuser/repo.git",
        }
        with make_remote_patch(remotes):
            result = classify_project(owned_remote_project, config)
        assert result.project_type is ProjectType.OWNED_REMOTE
        assert result.remote_url == "git@github.com:testuser/repo.git"

    def test_fallback_to_first_remote_when_no_origin(
        self, owned_remote_project: Path, config: Config
    ) -> None:
        """When no origin, use the first available remote."""
        remotes = {"upstream": "git@github.com:testuser/repo.git"}
        with make_remote_patch(remotes):
            result = classify_project(owned_remote_project, config)
        assert result.project_type is ProjectType.OWNED_REMOTE

    def test_project_path_preserved(
        self, empty_dir: Path, config: Config
    ) -> None:
        result = classify_project(empty_dir, config)
        assert result.path == empty_dir


# get_git_remotes tests live in tests/test_git.py since the function
# now lives in devfolder.git.
