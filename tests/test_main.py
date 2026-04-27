"""Integration tests for the devfolder CLI entry point."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from devfolder import main

from .conftest import git_commit, init_git_repo, make_remote_patch


class TestMain:
    """Tests for the main() CLI entry point."""

    def test_scan_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`devfolder scan <dir>` scans and prints a tree."""
        root = tmp_path / "dev"
        root.mkdir()
        category = root / "tools"
        category.mkdir()
        project = category / "my-project"
        project.mkdir()
        (project / "main.py").write_text("")

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[[owners]]\nname = "testuser"\nhost = "github.com"\n'
        )

        with (
            patch(
                "sys.argv",
                ["devfolder", "scan", str(root), "--config", str(config_file)],
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
        """`devfolder scan` handles a root that is itself a project."""
        root = tmp_path / "project"
        root.mkdir()
        (root / ".git").mkdir()
        (root / "main.py").write_text("")

        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        with (
            patch(
                "sys.argv",
                ["devfolder", "scan", str(root), "--config", str(config_file)],
            ),
            make_remote_patch({}),
        ):
            main()

        output = capsys.readouterr().out
        assert "[local-git]" in output

    def test_scan_nonexistent_path_exits(self, tmp_path: Path) -> None:
        """`devfolder scan <missing>` exits with code 1."""
        missing = tmp_path / "does-not-exist"

        with (
            patch("sys.argv", ["devfolder", "scan", str(missing)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_scan_file_path_exits(self, tmp_path: Path) -> None:
        """`devfolder scan <file>` exits with code 1."""
        f = tmp_path / "file.txt"
        f.write_text("hello")

        with (
            patch("sys.argv", ["devfolder", "scan", str(f)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """`devfolder --version` prints version to stdout and exits 0."""
        from importlib.metadata import version

        with (
            patch("sys.argv", ["devfolder", "--version"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == f"devfolder {version('devfolder')}"

    def test_scan_default_root_is_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`devfolder scan` (no root) uses the current working directory."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        monkeypatch.chdir(tmp_path)

        with (
            patch(
                "sys.argv",
                ["devfolder", "scan", "--config", str(config_file)],
            ),
            make_remote_patch({}),
        ):
            main()

        output = capsys.readouterr().out
        assert str(tmp_path) in output

    def test_no_subcommand_exits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`devfolder` (no subcommand) exits with usage error."""
        with (
            patch("sys.argv", ["devfolder"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        # argparse uses exit code 2 for usage errors
        assert exc_info.value.code == 2

    def test_bare_path_invocation_rejected(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`devfolder <path>` (no subcommand) is rejected.

        Hard break from pre-0.3.0 single-positional CLI.
        """
        with (
            patch("sys.argv", ["devfolder", str(tmp_path)]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 2


class TestOutputFormats:
    """Tests for --output and --output-file CLI flags."""

    def _make_scannable_dir(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a simple scannable directory and config file.

        Returns:
            A tuple of (root directory, config file path).
        """
        root = tmp_path / "dev"
        root.mkdir()
        category = root / "tools"
        category.mkdir()
        project = category / "my-project"
        project.mkdir()
        (project / "main.py").write_text("")

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[[owners]]\nname = "testuser"\nhost = "github.com"\n'
        )
        return root, config_file

    def test_json_to_default_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`scan -o json` with no -f writes devfolder.json in CWD."""
        root, config_file = self._make_scannable_dir(tmp_path)
        monkeypatch.chdir(tmp_path)

        with (
            patch(
                "sys.argv",
                [
                    "devfolder",
                    "scan",
                    str(root),
                    "--config",
                    str(config_file),
                    "-o",
                    "json",
                ],
            ),
            make_remote_patch({}),
        ):
            main()

        output_file = tmp_path / "devfolder.json"
        assert output_file.exists()
        parsed = json.loads(output_file.read_text())
        assert parsed["root"] == str(root)
        assert isinstance(parsed["children"], list)

        captured = capsys.readouterr()
        assert "devfolder.json" in captured.err
        assert captured.out == ""

    def test_json_to_explicit_file(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`scan -o json -f custom.json` writes to the specified file."""
        root, config_file = self._make_scannable_dir(tmp_path)
        output_path = tmp_path / "custom.json"

        with (
            patch(
                "sys.argv",
                [
                    "devfolder",
                    "scan",
                    str(root),
                    "--config",
                    str(config_file),
                    "-o",
                    "json",
                    "-f",
                    str(output_path),
                ],
            ),
            make_remote_patch({}),
        ):
            main()

        assert output_path.exists()
        parsed = json.loads(output_path.read_text())
        assert parsed["root"] == str(root)

        captured = capsys.readouterr()
        assert str(output_path) in captured.err

    def test_text_to_file(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`scan -f tree.txt` writes tree text to a file."""
        root, config_file = self._make_scannable_dir(tmp_path)
        output_path = tmp_path / "tree.txt"

        with (
            patch(
                "sys.argv",
                [
                    "devfolder",
                    "scan",
                    str(root),
                    "--config",
                    str(config_file),
                    "-f",
                    str(output_path),
                ],
            ),
            make_remote_patch({}),
        ):
            main()

        assert output_path.exists()
        content = output_path.read_text()
        assert "tools/" in content
        assert "my-project/" in content

        captured = capsys.readouterr()
        assert str(output_path) in captured.err
        assert captured.out == ""

    def test_text_to_stdout_unchanged(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Default text output still prints to stdout."""
        root, config_file = self._make_scannable_dir(tmp_path)

        with (
            patch(
                "sys.argv",
                ["devfolder", "scan", str(root), "--config", str(config_file)],
            ),
            make_remote_patch({}),
        ):
            main()

        captured = capsys.readouterr()
        assert "tools/" in captured.out
        assert captured.err == ""


class TestInspectCommand:
    """Integration tests for `devfolder inspect <path>`."""

    def test_inspect_git_repo_text(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo = tmp_path / "repo"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        with patch("sys.argv", ["devfolder", "inspect", str(repo)]):
            main()

        out = capsys.readouterr().out
        assert "(git)" in out
        assert "Working tree:" in out
        assert "Branches:" in out
        assert "Last commit:" in out

    def test_inspect_git_repo_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo = tmp_path / "repo"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        with patch(
            "sys.argv", ["devfolder", "inspect", str(repo), "-o", "json"]
        ):
            main()

        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["kind"] == "git"
        assert parsed["path"] == str(repo)
        assert parsed["working_tree"]["clean"] is True

    def test_inspect_non_git_dir_text(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        d = tmp_path / "plain"
        d.mkdir()
        (d / "a.txt").write_text("hello")

        with patch("sys.argv", ["devfolder", "inspect", str(d)]):
            main()

        out = capsys.readouterr().out
        assert "(non-git)" in out
        assert "Files:" in out
        assert "Folders:" in out

    def test_inspect_non_git_dir_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        d = tmp_path / "plain"
        d.mkdir()
        (d / "a.txt").write_text("hello")

        with patch(
            "sys.argv", ["devfolder", "inspect", str(d), "-o", "json"]
        ):
            main()

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["kind"] == "non-git"
        assert parsed["file_count"] == 1

    def test_inspect_to_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        d = tmp_path / "plain"
        d.mkdir()
        (d / "a.txt").write_text("hello")
        out_path = tmp_path / "inspect.json"

        with patch(
            "sys.argv",
            [
                "devfolder",
                "inspect",
                str(d),
                "-o",
                "json",
                "-f",
                str(out_path),
            ],
        ):
            main()

        assert out_path.exists()
        parsed = json.loads(out_path.read_text())
        assert parsed["kind"] == "non-git"

        captured = capsys.readouterr()
        assert str(out_path) in captured.err
        assert captured.out == ""

    def test_inspect_nonexistent_path_exits(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"

        with (
            patch("sys.argv", ["devfolder", "inspect", str(missing)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_inspect_file_path_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")

        with (
            patch("sys.argv", ["devfolder", "inspect", str(f)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()


class TestReportCommand:
    """Integration tests for `devfolder report <root>`."""

    def _make_report_tree(self, tmp_path: Path) -> tuple[Path, Path]:
        """Build a tree with one git project under a category."""
        root = tmp_path / "dev"
        root.mkdir()
        cat = root / "tools"
        cat.mkdir()
        repo = cat / "repo"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)

        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        return root, config_file

    def test_report_writes_default_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`devfolder report <root>` defaults to ./report.json."""
        root, config_file = self._make_report_tree(tmp_path)
        monkeypatch.chdir(tmp_path)

        with patch(
            "sys.argv",
            ["devfolder", "report", str(root), "--config", str(config_file)],
        ):
            main()

        out_file = tmp_path / "report.json"
        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        # Augmented project has an inspect field
        tools = parsed["children"][0]
        repo_node = tools["children"][0]
        assert "inspect" in repo_node
        assert repo_node["inspect"]["kind"] == "git"

        captured = capsys.readouterr()
        # Stderr carries progress + summary; stdout stays empty
        assert "Inspecting project" in captured.err
        assert "report.json" in captured.err
        assert captured.out == ""

    def test_report_writes_explicit_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root, config_file = self._make_report_tree(tmp_path)
        out_path = tmp_path / "custom.json"

        with patch(
            "sys.argv",
            [
                "devfolder",
                "report",
                str(root),
                "--config",
                str(config_file),
                "-f",
                str(out_path),
            ],
        ):
            main()

        assert out_path.exists()
        parsed = json.loads(out_path.read_text())
        assert parsed["root"] == str(root)

        captured = capsys.readouterr()
        assert str(out_path) in captured.err

    def test_report_progress_lines_to_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Progress format matches `Inspecting project N of M: <path>`."""
        root, config_file = self._make_report_tree(tmp_path)
        out_path = tmp_path / "r.json"

        with patch(
            "sys.argv",
            [
                "devfolder",
                "report",
                str(root),
                "--config",
                str(config_file),
                "-f",
                str(out_path),
            ],
        ):
            main()

        err = capsys.readouterr().err
        assert "Inspecting project 1 of 1:" in err

    def test_report_nonexistent_path_exits(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"

        with (
            patch("sys.argv", ["devfolder", "report", str(missing)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_report_file_path_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")

        with (
            patch("sys.argv", ["devfolder", "report", str(f)]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()
