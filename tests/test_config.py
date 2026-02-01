"""Tests for devfolder.config module."""

from pathlib import Path

from devfolder.config import Config


class TestConfig:
    """Tests for configuration loading."""

    def test_default_config(self) -> None:
        config = Config()
        assert config.username is None

    def test_config_with_username(self) -> None:
        config = Config(username="testuser")
        assert config.username == "testuser"

    def test_config_is_frozen(self) -> None:
        config = Config(username="testuser")
        try:
            config.username = "other"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_load_valid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('username = "myuser"\n')

        config = Config.load(config_file)

        assert config.username == "myuser"

    def test_load_missing_config_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / "nonexistent.toml"
        config = Config.load(missing)
        assert config.username is None

    def test_load_empty_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        config = Config.load(config_file)

        assert config.username is None

    def test_load_invalid_toml_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is not valid toml {{{{")

        config = Config.load(config_file)

        assert config.username is None

    def test_load_config_with_extra_keys(
        self, tmp_path: Path
    ) -> None:
        """Extra keys in config should be ignored gracefully."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'username = "myuser"\nunknown_key = "value"\n'
        )

        config = Config.load(config_file)

        assert config.username == "myuser"

    def test_load_non_string_username_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        """A non-string username value should be treated as invalid."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("username = 42\n")

        config = Config.load(config_file)

        assert config.username is None

    def test_default_path(self) -> None:
        path = Config.default_path()
        assert path.name == "config.toml"
        assert "devfolder" in str(path)
