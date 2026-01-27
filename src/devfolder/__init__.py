"""DevFolder - A CLI tool to scan and categorize local development projects."""

import argparse
import sys
from pathlib import Path

from .config import Config
from .output import format_tree
from .scanner import scan

__all__ = ["main"]


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="devfolder",
        description="Scan and categorize local development projects",
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config file (default: ~/.config/devfolder/config.toml)",
    )
    return parser


def main() -> None:
    """Main entry point for the devfolder CLI."""
    parser = create_parser()
    args = parser.parse_args()

    root: Path = args.root
    config_path: Path | None = args.config

    # Validate root path
    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if not root.is_dir():
        print(f"Error: Path is not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    config = Config.load(config_path)

    # Scan and output
    result = scan(root, config)
    output = format_tree(result)
    print(output)
