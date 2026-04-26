"""DevFolder - A CLI tool to scan and categorize local development projects."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from .config import Config
from .output import format_tree
from .scanner import scan
from .serializers import format_json

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
        "--version",
        action="version",
        version=f"%(prog)s {version('devfolder')}",
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
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output-file",
        "-f",
        type=Path,
        default=None,
        help="Write output to a file instead of stdout",
    )
    return parser


def main() -> None:
    """Main entry point for the devfolder CLI."""
    parser = create_parser()
    args = parser.parse_args()

    root: Path = args.root
    config_path: Path | None = args.config
    output_format: str = args.output
    output_file: Path | None = args.output_file

    # Validate root path
    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if not root.is_dir():
        print(f"Error: Path is not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    config = Config.load(config_path)

    # Scan and format
    result = scan(root, config)

    if output_format == "json":
        output = format_json(result)
    else:
        output = format_tree(result)

    # Default JSON output to devfolder.json in CWD when no file specified
    if output_format == "json" and output_file is None:
        output_file = Path.cwd() / "devfolder.json"

    # Write to file or stdout
    if output_file is not None:
        output_file.write_text(output + "\n")
        print(f"Output written to {output_file}", file=sys.stderr)
    else:
        print(output)
