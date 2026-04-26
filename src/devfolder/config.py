"""Configuration loading for devfolder."""

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .models import Owner

__all__ = ["Config"]


@dataclass(frozen=True)
class Config:
    """Configuration for devfolder."""

    owners: tuple[Owner, ...] = field(default_factory=tuple)

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

        owners = _parse_owners(data.get("owners"), config_path)
        return cls(owners=owners)


def _parse_owners(raw: object, config_path: Path) -> tuple[Owner, ...]:
    """Parse the `owners` array from config data.

    Malformed entries are skipped with a warning; valid entries are kept.

    Args:
        raw: The raw value of the `owners` key from TOML.
        config_path: The config file path, for warning messages.

    Returns:
        A tuple of valid Owner records.
    """
    if raw is None:
        return ()

    if not isinstance(raw, list):
        print(
            f"warning: {config_path}: 'owners' must be an array of tables, "
            f"got {type(raw).__name__}; ignoring",
            file=sys.stderr,
        )
        return ()

    owners: list[Owner] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            print(
                f"warning: {config_path}: owners[{i}] is not a table; skipping",
                file=sys.stderr,
            )
            continue

        name = entry.get("name")
        host = entry.get("host")
        if not isinstance(name, str) or not isinstance(host, str):
            print(
                f"warning: {config_path}: owners[{i}] requires string "
                f"'name' and 'host' fields; skipping",
                file=sys.stderr,
            )
            continue

        owners.append(Owner(name=name, host=host))

    return tuple(owners)
