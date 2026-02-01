"""Tests for devfolder.scanner module."""

from pathlib import Path

import pytest

from devfolder.config import Config
from devfolder.models import (
    CategoryNode,
    IgnoredNode,
    IgnoreReason,
    NodeKind,
    ProjectNode,
    ProjectType,
    SymlinkNode,
)
from devfolder.scanner import scan, scan_category, should_ignore

from .conftest import make_remote_patch

# --- should_ignore ---


class TestShouldIgnore:
    """Tests for the should_ignore function."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            (".git", IgnoreReason.DOTFOLDER),
            (".config", IgnoreReason.DOTFOLDER),
            (".hidden", IgnoreReason.DOTFOLDER),
            ("node_modules", IgnoreReason.NODE_MODULES),
        ],
        ids=["dotgit", "dotconfig", "dothidden", "node-modules"],
    )
    def test_ignored_entries(
        self, tmp_path: Path, name: str, expected: IgnoreReason
    ) -> None:
        entry = tmp_path / name
        entry.mkdir()
        assert should_ignore(entry) == expected

    @pytest.mark.parametrize(
        "name",
        ["src", "tools", "my-project", "README.md"],
        ids=["src", "tools", "my-project", "readme"],
    )
    def test_not_ignored_entries(
        self, tmp_path: Path, name: str
    ) -> None:
        entry = tmp_path / name
        entry.mkdir()
        assert should_ignore(entry) is None


# --- scan_category ---


class TestScanCategory:
    """Tests for scanning a category directory."""

    def test_category_with_projects(
        self, tmp_path: Path, config: Config
    ) -> None:
        """A category with untracked projects."""
        category = tmp_path / "tools"
        category.mkdir()
        (category / "project-a").mkdir()
        (category / "project-a" / "main.py").write_text("")
        (category / "project-b").mkdir()
        (category / "project-b" / "main.py").write_text("")

        children = scan_category(category, config)

        assert len(children) == 2
        assert all(c.kind is NodeKind.PROJECT for c in children)
        names = [c.name for c in children]
        assert "project-a" in names
        assert "project-b" in names

    def test_category_with_symlink(
        self, tmp_path: Path, config: Config
    ) -> None:
        category = tmp_path / "tools"
        category.mkdir()
        target = tmp_path / "target"
        target.mkdir()
        (category / "link").symlink_to(target)

        children = scan_category(category, config)

        assert len(children) == 1
        assert children[0].kind is NodeKind.SYMLINK
        assert isinstance(children[0], SymlinkNode)
        assert children[0].name == "link"

    def test_category_with_ignored_entries(
        self, tmp_path: Path, config: Config
    ) -> None:
        category = tmp_path / "tools"
        category.mkdir()
        (category / ".hidden").mkdir()
        (category / "node_modules").mkdir()

        children = scan_category(category, config)

        assert len(children) == 2
        assert all(c.kind is NodeKind.IGNORED for c in children)
        ignored = {c.name: c for c in children}
        hidden = ignored[".hidden"]
        assert isinstance(hidden, IgnoredNode)
        assert hidden.reason is IgnoreReason.DOTFOLDER
        nm = ignored["node_modules"]
        assert isinstance(nm, IgnoredNode)
        assert nm.reason is IgnoreReason.NODE_MODULES

    def test_category_skips_symlinked_files(
        self, tmp_path: Path, config: Config
    ) -> None:
        """Symlinked files should be excluded, same as regular files."""
        category = tmp_path / "tools"
        category.mkdir()
        target_file = tmp_path / "some-file.txt"
        target_file.write_text("hello")
        (category / "link-to-file").symlink_to(target_file)
        (category / "project-a").mkdir()
        (category / "project-a" / "main.py").write_text("")

        children = scan_category(category, config)

        assert len(children) == 1
        assert children[0].name == "project-a"

    def test_category_includes_symlinked_dirs(
        self, tmp_path: Path, config: Config
    ) -> None:
        """Symlinked directories should appear as symlink nodes."""
        category = tmp_path / "tools"
        category.mkdir()
        target_dir = tmp_path / "real-project"
        target_dir.mkdir()
        (category / "link-to-dir").symlink_to(target_dir)

        children = scan_category(category, config)

        assert len(children) == 1
        assert children[0].kind is NodeKind.SYMLINK
        assert isinstance(children[0], SymlinkNode)
        assert children[0].name == "link-to-dir"

    def test_category_skips_files(
        self, tmp_path: Path, config: Config
    ) -> None:
        """Regular files at category level should be skipped."""
        category = tmp_path / "tools"
        category.mkdir()
        (category / "README.md").write_text("# Tools")
        (category / "project-a").mkdir()
        (category / "project-a" / "main.py").write_text("")

        children = scan_category(category, config)

        assert len(children) == 1
        assert children[0].name == "project-a"

    def test_empty_category(
        self, tmp_path: Path, config: Config
    ) -> None:
        category = tmp_path / "empty"
        category.mkdir()

        children = scan_category(category, config)

        assert len(children) == 0

    def test_children_sorted_alphabetically(
        self, tmp_path: Path, config: Config
    ) -> None:
        category = tmp_path / "tools"
        category.mkdir()
        for name in ["zebra", "alpha", "middle"]:
            d = category / name
            d.mkdir()
            (d / "file.txt").write_text("")

        children = scan_category(category, config)

        names = [c.name for c in children]
        assert names == ["alpha", "middle", "zebra"]


# --- scan ---


class TestScan:
    """Tests for the top-level scan function."""

    def test_root_is_project(
        self, root_is_project: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = scan(root_is_project, config)

        assert result.is_root_project is True
        assert result.root_project is not None
        assert result.root_project.project_type is ProjectType.LOCAL_GIT
        assert len(result.children) == 0

    def test_two_level_structure(
        self, dev_folder: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = scan(dev_folder, config)

        assert result.is_root_project is False
        assert result.root == dev_folder

        children_by_name = {c.name: c for c in result.children}

        # Categories
        assert "tools" in children_by_name
        tools = children_by_name["tools"]
        assert tools.kind is NodeKind.CATEGORY
        assert isinstance(tools, CategoryNode)
        assert len(tools.children) == 2

        # Empty category
        assert "experiments" in children_by_name
        experiments = children_by_name["experiments"]
        assert experiments.kind is NodeKind.CATEGORY
        assert isinstance(experiments, CategoryNode)
        assert experiments.is_empty is True

        # Scratch category with mixed children
        assert "scratch" in children_by_name
        scratch = children_by_name["scratch"]
        assert scratch.kind is NodeKind.CATEGORY
        assert isinstance(scratch, CategoryNode)
        assert len(scratch.children) == 2

    def test_ignored_nodes(
        self, dev_folder: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = scan(dev_folder, config)

        children_by_name = {c.name: c for c in result.children}

        # Dotfolder
        assert ".config" in children_by_name
        dotconfig = children_by_name[".config"]
        assert dotconfig.kind is NodeKind.IGNORED
        assert isinstance(dotconfig, IgnoredNode)
        assert dotconfig.reason is IgnoreReason.DOTFOLDER

        # node_modules
        assert "node_modules" in children_by_name
        nm = children_by_name["node_modules"]
        assert nm.kind is NodeKind.IGNORED
        assert isinstance(nm, IgnoredNode)
        assert nm.reason is IgnoreReason.NODE_MODULES

    def test_symlink_detected(
        self, dev_folder: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = scan(dev_folder, config)

        children_by_name = {c.name: c for c in result.children}

        assert "link" in children_by_name
        link = children_by_name["link"]
        assert link.kind is NodeKind.SYMLINK
        assert isinstance(link, SymlinkNode)
        assert link.target is not None

    def test_category_level_project(
        self, dev_folder: Path, config: Config
    ) -> None:
        """A folder with .git at category level is treated as a project."""
        with make_remote_patch({}):
            result = scan(dev_folder, config)

        children_by_name = {c.name: c for c in result.children}

        assert "git-at-root" in children_by_name
        git_at_root = children_by_name["git-at-root"]
        assert git_at_root.kind is NodeKind.PROJECT
        assert isinstance(git_at_root, ProjectNode)
        assert git_at_root.project_type is ProjectType.LOCAL_GIT

    def test_children_sorted(
        self, dev_folder: Path, config: Config
    ) -> None:
        with make_remote_patch({}):
            result = scan(dev_folder, config)

        names = [c.name for c in result.children]
        assert names == sorted(names, key=str.lower)

    def test_symlinked_file_excluded(
        self, tmp_path: Path, config: Config
    ) -> None:
        """Symlinked files at root level should be excluded from the tree."""
        root = tmp_path / "dev"
        root.mkdir()
        target_file = tmp_path / "some-file.txt"
        target_file.write_text("hello")
        (root / "link-to-file").symlink_to(target_file)
        # Add a symlinked directory too, to verify it IS included
        target_dir = tmp_path / "real-project"
        target_dir.mkdir()
        (root / "link-to-dir").symlink_to(target_dir)

        result = scan(root, config)

        children_by_name = {c.name: c for c in result.children}
        assert "link-to-file" not in children_by_name
        assert "link-to-dir" in children_by_name
        assert children_by_name["link-to-dir"].kind is NodeKind.SYMLINK

    def test_root_resolves_to_absolute(
        self, tmp_path: Path, config: Config
    ) -> None:
        d = tmp_path / "test"
        d.mkdir()
        result = scan(d, config)
        assert result.root.is_absolute()

    def test_empty_root(
        self, tmp_path: Path, config: Config
    ) -> None:
        """A root directory with no subdirectories."""
        root = tmp_path / "empty-root"
        root.mkdir()

        result = scan(root, config)

        assert result.is_root_project is False
        assert len(result.children) == 0

    def test_root_with_only_files(
        self, tmp_path: Path, config: Config
    ) -> None:
        """A root directory with only regular files (no directories)."""
        root = tmp_path / "files-only"
        root.mkdir()
        (root / "README.md").write_text("hello")
        (root / "notes.txt").write_text("notes")

        result = scan(root, config)

        assert len(result.children) == 0
