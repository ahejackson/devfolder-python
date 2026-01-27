"""Configuration loading for devfolder."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Configuration for devfolder."""

    username: str | None = None

    @classmethod
    def default_path(cls) -> Path:
        """Get the default configuration file path."""
        return Path.home() / ".config" / "devfolder" / "config.toml"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from a TOML file.

        Args:
            path: Path to the config file. If None, uses the default location.

        Returns:
            A Config instance with loaded values, or defaults if file doesn't exist.
        """
        config_path = path if path is not None else cls.default_path()

        if not config_path.exists():
            return cls()

        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return cls()

        return cls(
            username=data.get("username"),
        )
