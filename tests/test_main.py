"""Integration tests for the devfolder CLI entry point."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from devfolder import main

from .conftest import make_remote_patch


class TestMain:
    """Tests for the main() CLI entry point."""

    def test_scan_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """main() scans a directory and prints a tree."""
        root = tmp_path / "dev"
        root.mkdir()
        category = root / "tools"
        category.mkdir()
        project = category / "my-project"
        project.mkdir()
        (project / "main.py").write_text("")

        config_file = tmp_path / "config.toml"
        config_file.write_text('username = "testuser"\n')

        with (
            patch(
                "sys.argv",
                ["devfolder", str(root), "--config", str(config_file)],
            ),
            make_remote_patch({}),
        ):
            main()

        output = capsys.readouterr().out
        assert "tools/" in output
        assert "my-project/" in output
        assert "[local-untracked]" in output

    def test_scan_root_project(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """main() handles a root that is itself a project."""
        root = tmp_path / "project"
        root.mkdir()
        (root / ".git").mkdir()
        (root / "main.py").write_text("")

        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        with (
            patch(
                "sys.argv",
                ["devfolder", str(root), "--config", str(config_file)],
            ),
            make_remote_patch({}),
        ):
            main()

        output = capsys.readouterr().out
        assert "[local-git]" in output

    def test_nonexistent_path_exits(self, tmp_path: Path) -> None:
        """main() exits with code 1 for a non-existent path."""
        missing = tmp_path / "does-not-exist"

        with (
            patch("sys.argv", ["devfolder", str(missing)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_file_path_exits(self, tmp_path: Path) -> None:
        """main() exits with code 1 when given a file instead of a dir."""
        f = tmp_path / "file.txt"
        f.write_text("hello")

        with (
            patch("sys.argv", ["devfolder", str(f)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_default_root_is_cwd(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With no arguments, main() uses the current working directory."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        with (
            patch(
                "sys.argv",
                ["devfolder", "--config", str(config_file)],
            ),
            patch("devfolder.create_parser") as mock_parser_fn,
        ):
            # Set up a mock parser that returns tmp_path as root
            mock_ns = type(sys)("mock_ns")
            mock_ns.root = tmp_path  # type: ignore[attr-defined]
            mock_ns.config = config_file  # type: ignore[attr-defined]
            mock_parser = mock_parser_fn.return_value
            mock_parser.parse_args.return_value = mock_ns
            main()

        output = capsys.readouterr().out
        assert str(tmp_path) in output
