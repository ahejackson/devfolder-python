"""Tests for devfolder.config module."""

from pathlib import Path

import pytest

from devfolder.config import Config
from devfolder.models import Owner


class TestConfig:
    """Tests for configuration loading."""

    def test_default_config(self) -> None:
        config = Config()
        assert config.owners == ()

    def test_config_with_owners(self) -> None:
        owners = (Owner(name="me", host="github.com"),)
        config = Config(owners=owners)
        assert config.owners == owners

    def test_config_is_frozen(self) -> None:
        config = Config(owners=(Owner(name="me", host="github.com"),))
        try:
            config.owners = ()  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_load_valid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[[owners]]\nname = \"me\"\nhost = \"github.com\"\n"
        )

        config = Config.load(config_file)

        assert config.owners == (Owner(name="me", host="github.com"),)

    def test_load_multiple_owners(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[[owners]]\nname = \"me\"\nhost = \"github.com\"\n"
            "[[owners]]\nname = \"my-org\"\nhost = \"github.com\"\n"
            "[[owners]]\nname = \"old-me\"\nhost = \"gitlab.com\"\n"
        )

        config = Config.load(config_file)

        assert config.owners == (
            Owner(name="me", host="github.com"),
            Owner(name="my-org", host="github.com"),
            Owner(name="old-me", host="gitlab.com"),
        )

    def test_load_missing_config_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / "nonexistent.toml"
        config = Config.load(missing)
        assert config.owners == ()

    def test_load_empty_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        config = Config.load(config_file)

        assert config.owners == ()

    def test_load_invalid_toml_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is not valid toml {{{{")

        config = Config.load(config_file)

        assert config.owners == ()

    def test_load_config_with_extra_keys_warns(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Unknown top-level keys are accepted but produce a warning."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "unknown_key = \"value\"\n"
            "[[owners]]\nname = \"me\"\nhost = \"github.com\"\n"
        )

        config = Config.load(config_file)

        assert config.owners == (Owner(name="me", host="github.com"),)
        captured = capsys.readouterr()
        assert "unknown_key" in captured.err
        assert "warning" in captured.err

    def test_load_legacy_username_key_warns(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The pre-0.2.0 `username` key is flagged as unknown, not silently ignored."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("username = \"ahejackson\"\n")

        config = Config.load(config_file)

        assert config.owners == ()
        captured = capsys.readouterr()
        assert "username" in captured.err
        assert "[[owners]]" in captured.err

    def test_load_no_owners_warns_when_file_exists(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An existing config file that yields zero owners produces a warning."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        config = Config.load(config_file)

        assert config.owners == ()
        captured = capsys.readouterr()
        assert "no [[owners]] configured" in captured.err

    def test_load_missing_config_does_not_warn(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A missing config file is a fresh-install state and stays silent."""
        missing = tmp_path / "nonexistent.toml"

        config = Config.load(missing)

        assert config.owners == ()
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_load_owners_not_an_array_warns_and_returns_empty(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A non-array `owners` value is rejected with a warning."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("owners = \"not-a-list\"\n")

        config = Config.load(config_file)

        assert config.owners == ()
        captured = capsys.readouterr()
        assert "warning" in captured.err
        assert "owners" in captured.err

    def test_load_skips_malformed_owner_entries(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Malformed owner entries are skipped; valid ones are kept."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[[owners]]\nname = \"good\"\nhost = \"github.com\"\n"
            "[[owners]]\nname = 42\nhost = \"github.com\"\n"
            "[[owners]]\nname = \"missing-host\"\n"
        )

        config = Config.load(config_file)

        assert config.owners == (Owner(name="good", host="github.com"),)
        captured = capsys.readouterr()
        # Two warnings: one for the int name, one for the missing host
        assert captured.err.count("warning") >= 2

    def test_default_path(self) -> None:
        path = Config.default_path()
        assert path.name == "config.toml"
        assert "devfolder" in str(path)
