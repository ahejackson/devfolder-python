"""Tests for devfolder.output module."""

from pathlib import Path

import pytest

from devfolder.models import (
    CategoryNode,
    ErrorNode,
    IgnoredNode,
    IgnoreReason,
    ProjectNode,
    ProjectType,
    ScanResult,
    SymlinkNode,
)
from devfolder.output import (
    format_ignore_reason,
    format_node,
    format_project_type,
    format_tree,
)

# --- format_project_type ---


class TestFormatProjectType:
    """Tests for project type formatting."""

    @pytest.mark.parametrize(
        ("project_type", "expected"),
        [
            (ProjectType.EMPTY, "[empty]"),
            (ProjectType.LOCAL_UNTRACKED, "[local-untracked]"),
            (ProjectType.LOCAL_GIT, "[local-git]"),
            (ProjectType.PERSONAL_REMOTE, "[personal-remote]"),
            (ProjectType.OTHER_REMOTE, "[other-remote]"),
        ],
    )
    def test_all_types(
        self, project_type: ProjectType, expected: str
    ) -> None:
        assert format_project_type(project_type) == expected


# --- format_ignore_reason ---


class TestFormatIgnoreReason:
    """Tests for ignore reason formatting."""

    def test_dotfolder(self) -> None:
        assert format_ignore_reason(IgnoreReason.DOTFOLDER) == "[ignored: dotfolder]"

    def test_node_modules(self) -> None:
        result = format_ignore_reason(IgnoreReason.NODE_MODULES)
        assert result == "[ignored: node_modules]"


# --- format_node ---


class TestFormatNode:
    """Tests for individual node formatting."""

    @pytest.fixture
    def base_path(self, tmp_path: Path) -> Path:
        return tmp_path / "test"

    def test_project_node_no_remote(self, base_path: Path) -> None:
        node = ProjectNode(
            name="my-project",
            path=base_path,
            project_type=ProjectType.LOCAL_GIT,
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert "my-project/" in lines[0]
        assert "[local-git]" in lines[0]
        assert lines[0].startswith("└──")

    def test_project_node_with_remote(self, base_path: Path) -> None:
        node = ProjectNode(
            name="my-project",
            path=base_path,
            project_type=ProjectType.PERSONAL_REMOTE,
            remote_url="git@github.com:user/repo.git",
        )
        lines = format_node(node, prefix="", is_last=False)

        assert len(lines) == 1
        assert "[personal-remote]" in lines[0]
        assert "git@github.com:user/repo.git" in lines[0]
        assert lines[0].startswith("├──")

    def test_category_node_with_children(self, base_path: Path) -> None:
        child = ProjectNode(
            name="child-project",
            path=base_path / "child",
            project_type=ProjectType.LOCAL_UNTRACKED,
        )
        node = CategoryNode(
            name="tools",
            path=base_path,
            children=(child,),
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 2
        assert "tools/" in lines[0]
        assert "[empty]" not in lines[0]
        assert "child-project/" in lines[1]
        assert "[local-untracked]" in lines[1]

    def test_empty_category_node(self, base_path: Path) -> None:
        node = CategoryNode(
            name="empty-cat",
            path=base_path,
            children=(),
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert "empty-cat/" in lines[0]
        assert "[empty]" in lines[0]

    def test_symlink_node(self, base_path: Path) -> None:
        node = SymlinkNode(
            name="link",
            path=base_path,
            target=Path("/some/target"),
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert "link" in lines[0]
        assert "-> /some/target" in lines[0]
        assert "[symlink]" in lines[0]

    def test_symlink_node_no_target(self, base_path: Path) -> None:
        node = SymlinkNode(
            name="broken-link",
            path=base_path,
            target=None,
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert "->" not in lines[0]
        assert "[symlink]" in lines[0]

    def test_ignored_node_dotfolder(self, base_path: Path) -> None:
        node = IgnoredNode(
            name=".config",
            path=base_path,
            reason=IgnoreReason.DOTFOLDER,
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert ".config/" in lines[0]
        assert "[ignored: dotfolder]" in lines[0]

    def test_ignored_node_node_modules(self, base_path: Path) -> None:
        node = IgnoredNode(
            name="node_modules",
            path=base_path,
            reason=IgnoreReason.NODE_MODULES,
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert "[ignored: node_modules]" in lines[0]

    def test_error_node(self, base_path: Path) -> None:
        node = ErrorNode(
            name="forbidden",
            path=base_path,
            error_message="Permission denied",
        )
        lines = format_node(node, prefix="", is_last=True)

        assert len(lines) == 1
        assert "forbidden/" in lines[0]
        assert "[error: Permission denied]" in lines[0]

    def test_not_last_uses_tee_connector(self, base_path: Path) -> None:
        node = ProjectNode(
            name="proj",
            path=base_path,
            project_type=ProjectType.EMPTY,
        )
        lines = format_node(node, prefix="", is_last=False)
        assert lines[0].startswith("├──")

    def test_last_uses_elbow_connector(self, base_path: Path) -> None:
        node = ProjectNode(
            name="proj",
            path=base_path,
            project_type=ProjectType.EMPTY,
        )
        lines = format_node(node, prefix="", is_last=True)
        assert lines[0].startswith("└──")

    def test_nested_indentation(self, base_path: Path) -> None:
        """Children of a non-last category use pipe indentation."""
        child = ProjectNode(
            name="child",
            path=base_path / "child",
            project_type=ProjectType.EMPTY,
        )
        node = CategoryNode(
            name="cat",
            path=base_path,
            children=(child,),
        )
        lines = format_node(node, prefix="", is_last=False)

        # Category line uses tee
        assert lines[0].startswith("├──")
        # Child line should be indented with pipe
        assert lines[1].startswith("│   └──")

    def test_last_nested_indentation(self, base_path: Path) -> None:
        """Children of a last category use space indentation."""
        child = ProjectNode(
            name="child",
            path=base_path / "child",
            project_type=ProjectType.EMPTY,
        )
        node = CategoryNode(
            name="cat",
            path=base_path,
            children=(child,),
        )
        lines = format_node(node, prefix="", is_last=True)

        # Category line uses elbow
        assert lines[0].startswith("└──")
        # Child line should be indented with spaces (no pipe)
        assert lines[1].startswith("    └──")


# --- format_tree ---


class TestFormatTree:
    """Tests for full tree formatting."""

    def test_root_project(self, tmp_path: Path) -> None:
        root_project = ProjectNode(
            name="my-project",
            path=tmp_path,
            project_type=ProjectType.LOCAL_GIT,
        )
        result = ScanResult(
            root=tmp_path,
            children=(),
            root_project=root_project,
        )
        output = format_tree(result)

        assert f"{tmp_path}/ [local-git]" in output

    def test_root_project_with_remote(self, tmp_path: Path) -> None:
        root_project = ProjectNode(
            name="my-project",
            path=tmp_path,
            project_type=ProjectType.PERSONAL_REMOTE,
            remote_url="git@github.com:user/repo.git",
        )
        result = ScanResult(
            root=tmp_path,
            children=(),
            root_project=root_project,
        )
        output = format_tree(result)

        assert "[personal-remote]" in output
        assert "git@github.com:user/repo.git" in output

    def test_non_project_root(self, tmp_path: Path) -> None:
        result = ScanResult(
            root=tmp_path,
            children=(),
        )
        output = format_tree(result)

        assert output == f"{tmp_path}/"

    def test_full_tree(self, tmp_path: Path) -> None:
        """A complete tree with mixed node types."""
        project = ProjectNode(
            name="proj",
            path=tmp_path / "cat" / "proj",
            project_type=ProjectType.OTHER_REMOTE,
            remote_url="https://github.com/org/repo.git",
        )
        category = CategoryNode(
            name="cat",
            path=tmp_path / "cat",
            children=(project,),
        )
        ignored = IgnoredNode(
            name=".hidden",
            path=tmp_path / ".hidden",
            reason=IgnoreReason.DOTFOLDER,
        )
        result = ScanResult(
            root=tmp_path,
            children=(category, ignored),
        )
        output = format_tree(result)
        lines = output.split("\n")

        assert lines[0] == f"{tmp_path}/"
        assert "cat/" in lines[1]
        assert "[other-remote]" in lines[2]
        assert "https://github.com/org/repo.git" in lines[2]
        assert "[ignored: dotfolder]" in lines[3]

    def test_tree_output_has_no_trailing_newline(
        self, tmp_path: Path
    ) -> None:
        result = ScanResult(root=tmp_path, children=())
        output = format_tree(result)
        assert not output.endswith("\n")
