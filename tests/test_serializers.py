"""Unit tests for devfolder JSON serialization."""

import json
from datetime import UTC, datetime
from pathlib import Path

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
from devfolder.serializers import format_json, node_to_dict, scan_result_to_dict


class TestNodeToDict:
    """Tests for node_to_dict()."""

    def test_project_node(self) -> None:
        """A project node includes kind, name, path, project_type, remote_url, owner."""
        node = ProjectNode(
            name="my-tool",
            path=Path("/dev/tools/my-tool"),
            project_type=ProjectType.LOCAL_GIT,
        )
        result = node_to_dict(node)
        assert result == {
            "kind": "project",
            "name": "my-tool",
            "path": "/dev/tools/my-tool",
            "project_type": "local-git",
            "remote_url": None,
            "owner": None,
        }

    def test_project_node_with_remote(self) -> None:
        """A project node with a remote URL and owner includes both in the output."""
        node = ProjectNode(
            name="my-tool",
            path=Path("/dev/tools/my-tool"),
            project_type=ProjectType.OWNED_REMOTE,
            remote_url="git@github.com:user/my-tool.git",
            owner="user",
        )
        result = node_to_dict(node)
        assert result["remote_url"] == "git@github.com:user/my-tool.git"
        assert result["project_type"] == "owned-remote"
        assert result["owner"] == "user"

    def test_category_node(self) -> None:
        """A category node includes kind, name, path, is_empty, and children."""
        child = ProjectNode(
            name="proj",
            path=Path("/dev/cat/proj"),
            project_type=ProjectType.EMPTY,
        )
        node = CategoryNode(
            name="cat",
            path=Path("/dev/cat"),
            children=(child,),
        )
        result = node_to_dict(node)
        assert result["kind"] == "category"
        assert result["is_empty"] is False
        assert isinstance(result["children"], list)
        assert len(result["children"]) == 1

    def test_category_node_empty(self) -> None:
        """An empty category node has is_empty=True and no children."""
        node = CategoryNode(name="empty", path=Path("/dev/empty"))
        result = node_to_dict(node)
        assert result["is_empty"] is True
        assert result["children"] == []

    def test_symlink_node(self) -> None:
        """A symlink node includes kind, name, path, and target."""
        node = SymlinkNode(
            name="link",
            path=Path("/dev/link"),
            target=Path("/dev/tools/my-tool"),
        )
        result = node_to_dict(node)
        assert result == {
            "kind": "symlink",
            "name": "link",
            "path": "/dev/link",
            "target": "/dev/tools/my-tool",
        }

    def test_symlink_node_no_target(self) -> None:
        """A symlink node with no target has target=None."""
        node = SymlinkNode(name="link", path=Path("/dev/link"))
        result = node_to_dict(node)
        assert result["target"] is None

    def test_ignored_node(self) -> None:
        """An ignored node includes kind, name, path, and reason."""
        node = IgnoredNode(
            name=".config",
            path=Path("/dev/.config"),
            reason=IgnoreReason.DOTFOLDER,
        )
        result = node_to_dict(node)
        assert result == {
            "kind": "ignored",
            "name": ".config",
            "path": "/dev/.config",
            "reason": "dotfolder",
        }

    def test_ignored_node_modules(self) -> None:
        """An ignored node_modules folder uses the node_modules reason."""
        node = IgnoredNode(
            name="node_modules",
            path=Path("/dev/node_modules"),
            reason=IgnoreReason.NODE_MODULES,
        )
        result = node_to_dict(node)
        assert result["reason"] == "node_modules"

    def test_error_node(self) -> None:
        """An error node includes kind, name, path, and error_message."""
        node = ErrorNode(
            name="forbidden",
            path=Path("/dev/forbidden"),
            error_message="Permission denied",
        )
        result = node_to_dict(node)
        assert result == {
            "kind": "error",
            "name": "forbidden",
            "path": "/dev/forbidden",
            "error_message": "Permission denied",
        }


class TestScanResultToDict:
    """Tests for scan_result_to_dict()."""

    def test_non_project_root(self) -> None:
        """A scan result for a non-project root has is_root_project=False."""
        child = ProjectNode(
            name="proj",
            path=Path("/dev/proj"),
            project_type=ProjectType.LOCAL_GIT,
        )
        result = ScanResult(root=Path("/dev"), children=(child,))
        d = scan_result_to_dict(result)
        assert d["root"] == "/dev"
        assert d["is_root_project"] is False
        assert d["root_project"] is None
        assert len(d["children"]) == 1  # type: ignore[arg-type]

    def test_root_is_project(self) -> None:
        """A scan result where root is a project includes root_project."""
        root_proj = ProjectNode(
            name="project",
            path=Path("/dev/project"),
            project_type=ProjectType.LOCAL_GIT,
        )
        result = ScanResult(
            root=Path("/dev/project"),
            children=(),
            root_project=root_proj,
        )
        d = scan_result_to_dict(result)
        assert d["is_root_project"] is True
        assert d["root_project"] is not None
        assert isinstance(d["root_project"], dict)

    def test_paths_become_strings(self) -> None:
        """All Path objects are converted to strings in the output."""
        result = ScanResult(root=Path("/dev"), children=())
        d = scan_result_to_dict(result)
        assert isinstance(d["root"], str)

    def test_generated_at_is_iso_string(self) -> None:
        """generated_at is serialized as an ISO 8601 string and round-trips."""
        ts = datetime(2026, 4, 26, 12, 30, 45, tzinfo=UTC)
        result = ScanResult(root=Path("/dev"), children=(), generated_at=ts)
        d = scan_result_to_dict(result)
        assert d["generated_at"] == "2026-04-26T12:30:45+00:00"
        assert datetime.fromisoformat(d["generated_at"]) == ts  # type: ignore[arg-type]

    def test_generated_at_default_is_now(self) -> None:
        """generated_at defaults to a tz-aware UTC timestamp at construction."""
        before = datetime.now(UTC)
        result = ScanResult(root=Path("/dev"), children=())
        after = datetime.now(UTC)
        assert result.generated_at.tzinfo is not None
        assert before <= result.generated_at <= after


class TestFormatJson:
    """Tests for format_json()."""

    def test_valid_json(self) -> None:
        """format_json() returns valid JSON."""
        result = ScanResult(root=Path("/dev"), children=())
        output = format_json(result)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_two_space_indentation(self) -> None:
        """format_json() uses 2-space indentation."""
        result = ScanResult(root=Path("/dev"), children=())
        output = format_json(result)
        # The "root" key should be indented with 2 spaces
        assert '\n  "root"' in output

    def test_full_tree_round_trip(self) -> None:
        """A full tree can be serialized and parsed back."""
        child_proj = ProjectNode(
            name="my-tool",
            path=Path("/dev/tools/my-tool"),
            project_type=ProjectType.OWNED_REMOTE,
            remote_url="git@github.com:user/my-tool.git",
            owner="user",
        )
        category = CategoryNode(
            name="tools",
            path=Path("/dev/tools"),
            children=(child_proj,),
        )
        symlink = SymlinkNode(
            name="link",
            path=Path("/dev/link"),
            target=Path("/dev/tools/my-tool"),
        )
        ignored = IgnoredNode(
            name=".config",
            path=Path("/dev/.config"),
            reason=IgnoreReason.DOTFOLDER,
        )
        error = ErrorNode(
            name="forbidden",
            path=Path("/dev/forbidden"),
            error_message="Permission denied",
        )
        result = ScanResult(
            root=Path("/dev"),
            children=(category, symlink, ignored, error),
        )

        output = format_json(result)
        parsed = json.loads(output)

        assert parsed["root"] == "/dev"
        assert parsed["is_root_project"] is False
        assert len(parsed["children"]) == 4
        assert parsed["children"][0]["kind"] == "category"
        assert parsed["children"][0]["children"][0]["kind"] == "project"
        assert parsed["children"][1]["kind"] == "symlink"
        assert parsed["children"][2]["kind"] == "ignored"
        assert parsed["children"][3]["kind"] == "error"
