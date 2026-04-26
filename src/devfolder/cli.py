"""CLI dispatch for devfolder."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from .config import Config
from .output import format_tree
from .scanner import scan
from .serializers import format_json

__all__ = ["create_parser", "main"]


def create_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser with all subcommands.

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

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="<command>",
    )

    _add_scan_parser(subparsers)

    return parser


def _add_scan_parser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Configure the `scan` subparser."""
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a directory tree and categorize projects",
        description="Scan a directory tree and categorize projects.",
    )
    scan_parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Root directory to scan (default: current directory)",
    )
    scan_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config file (default: ~/.config/devfolder/config.toml)",
    )
    scan_parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    scan_parser.add_argument(
        "--output-file",
        "-f",
        type=Path,
        default=None,
        help="Write output to a file instead of stdout",
    )


def main() -> None:
    """Main entry point for the devfolder CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "scan":
        _run_scan(args)


def _run_scan(args: argparse.Namespace) -> None:
    """Execute the `scan` subcommand."""
    root: Path = args.root
    config_path: Path | None = args.config
    output_format: str = args.output
    output_file: Path | None = args.output_file

    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if not root.is_dir():
        print(f"Error: Path is not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    config = Config.load(config_path)
    result = scan(root, config)

    if output_format == "json":
        output = format_json(result)
    else:
        output = format_tree(result)

    if output_format == "json" and output_file is None:
        output_file = Path.cwd() / "devfolder.json"

    if output_file is not None:
        output_file.write_text(output + "\n")
        print(f"Output written to {output_file}", file=sys.stderr)
    else:
        print(output)
