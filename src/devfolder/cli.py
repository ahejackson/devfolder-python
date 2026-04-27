"""CLI dispatch for devfolder."""

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

from .config import Config
from .inspector import inspect
from .output import format_inspect_text, format_tree
from .report import run_report
from .scanner import scan
from .serializers import format_inspect_json, format_json

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
    _add_inspect_parser(subparsers)
    _add_report_parser(subparsers)

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


def _add_inspect_parser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Configure the `inspect` subparser."""
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Collect detailed data for a single project",
        description=(
            "Collect detailed per-project data: working tree state, "
            "branches, stash, last commit, remotes (for git projects); "
            "or file/folder counts and total size (for non-git projects)."
        ),
    )
    inspect_parser.add_argument(
        "path",
        type=Path,
        help="Project directory to inspect",
    )
    inspect_parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    inspect_parser.add_argument(
        "--output-file",
        "-f",
        type=Path,
        default=None,
        help="Write output to a file instead of stdout",
    )


def _add_report_parser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Configure the `report` subparser."""
    report_parser = subparsers.add_parser(
        "report",
        help="Scan a tree and inspect every project (single JSON document)",
        description=(
            "Scan a directory tree and run inspect on every project. "
            "Emits a single augmented JSON document — the scan output "
            "with each project node carrying its inspect record. "
            "Progress is written to stderr; the JSON is written to a "
            "file (default: report.json in CWD)."
        ),
    )
    report_parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Root directory to scan (default: current directory)",
    )
    report_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config file (default: ~/.config/devfolder/config.toml)",
    )
    report_parser.add_argument(
        "--output-file",
        "-f",
        type=Path,
        default=None,
        help="Output file (default: report.json in CWD)",
    )


def main() -> None:
    """Main entry point for the devfolder CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "scan":
        _run_scan(args)
    elif args.command == "inspect":
        _run_inspect(args)
    elif args.command == "report":
        _run_report(args)


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


def _run_inspect(args: argparse.Namespace) -> None:
    """Execute the `inspect` subcommand."""
    path: Path = args.path
    output_format: str = args.output
    output_file: Path | None = args.output_file

    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    if not path.is_dir():
        print(f"Error: Path is not a directory: {path}", file=sys.stderr)
        sys.exit(1)

    result = inspect(path)

    if output_format == "json":
        output = format_inspect_json(result)
    else:
        output = format_inspect_text(result)

    if output_file is not None:
        output_file.write_text(output + "\n")
        print(f"Output written to {output_file}", file=sys.stderr)
    else:
        print(output)


def _run_report(args: argparse.Namespace) -> None:
    """Execute the `report` subcommand."""
    root: Path = args.root
    config_path: Path | None = args.config
    output_file: Path | None = args.output_file

    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if not root.is_dir():
        print(f"Error: Path is not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    config = Config.load(config_path)

    def on_progress(current: int, total: int, project_path: Path) -> None:
        print(
            f"Inspecting project {current} of {total}: {project_path}",
            file=sys.stderr,
        )

    document = run_report(root, config, on_progress=on_progress)

    if output_file is None:
        output_file = Path.cwd() / "report.json"

    output_file.write_text(json.dumps(document, indent=2) + "\n")
    print(f"Report written to {output_file}", file=sys.stderr)
