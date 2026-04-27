"""Unit tests for devfolder JSON serialization."""

import json
from datetime import UTC, datetime
from pathlib import Path

from devfolder.models import (
    BranchSummary,
    CategoryNode,
    ErrorNode,
    GitInspectResult,
    IgnoredNode,
    IgnoreReason,
    NonGitInspectResult,
    ProjectNode,
    ProjectType,
    RemoteRecord,
    ScanResult,
    SymlinkNode,
    WorkingTreeState,
)
from devfolder.serializers import (
    format_inspect_json,
    format_json,
    inspect_to_dict,
    node_to_dict,
    scan_result_to_dict,
)


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


class TestInspectToDict:
    """Tests for inspect_to_dict()."""

    def test_git_result_full_shape(self) -> None:
        last_commit = datetime(2026, 4, 26, 22, 58, tzinfo=UTC)
        mtime = datetime(2026, 4, 27, 18, 0, tzinfo=UTC)
        scanned = datetime(2026, 4, 27, 18, 30, tzinfo=UTC)
        result = GitInspectResult(
            path=Path("/dev/repo"),
            working_tree=WorkingTreeState(
                clean=False, staged=1, modified=2, untracked=3
            ),
            branches=BranchSummary(
                total=4, no_upstream=1, ahead_of_upstream=2
            ),
            stash_count=5,
            last_commit_at=last_commit,
            mtime=mtime,
            remotes=(
                RemoteRecord(
                    name="origin",
                    url="git@github.com:owner/repo.git",
                    host="github.com",
                    owner="owner",
                    repo="repo",
                ),
            ),
            scanned_at=scanned,
        )

        d = inspect_to_dict(result)

        assert d["kind"] == "git"
        assert d["path"] == "/dev/repo"
        assert d["working_tree"] == {
            "clean": False,
            "staged": 1,
            "modified": 2,
            "untracked": 3,
        }
        assert d["branches"] == {
            "total": 4,
            "no_upstream": 1,
            "ahead_of_upstream": 2,
        }
        assert d["stash_count"] == 5
        assert d["last_commit_at"] == "2026-04-26T22:58:00+00:00"
        assert d["mtime"] == "2026-04-27T18:00:00+00:00"
        assert d["scanned_at"] == "2026-04-27T18:30:00+00:00"
        remotes_field = d["remotes"]
        assert isinstance(remotes_field, list) and len(remotes_field) == 1
        assert remotes_field[0]["host"] == "github.com"
        assert remotes_field[0]["owner"] == "owner"
        assert remotes_field[0]["repo"] == "repo"

    def test_git_result_with_no_last_commit(self) -> None:
        """An empty repo serialises last_commit_at as null."""
        mtime = datetime(2026, 4, 27, 18, 0, tzinfo=UTC)
        scanned = datetime(2026, 4, 27, 18, 30, tzinfo=UTC)
        result = GitInspectResult(
            path=Path("/dev/empty"),
            working_tree=WorkingTreeState(
                clean=True, staged=0, modified=0, untracked=0
            ),
            branches=BranchSummary(
                total=0, no_upstream=0, ahead_of_upstream=0
            ),
            stash_count=0,
            last_commit_at=None,
            mtime=mtime,
            remotes=(),
            scanned_at=scanned,
        )

        d = inspect_to_dict(result)
        assert d["last_commit_at"] is None

    def test_non_git_result_full_shape(self) -> None:
        mtime = datetime(2026, 4, 27, 18, 0, tzinfo=UTC)
        scanned = datetime(2026, 4, 27, 18, 30, tzinfo=UTC)
        result = NonGitInspectResult(
            path=Path("/dev/plain"),
            file_count=10,
            folder_count=3,
            total_size_bytes=4096,
            mtime=mtime,
            scanned_at=scanned,
        )

        d = inspect_to_dict(result)
        assert d == {
            "kind": "non-git",
            "path": "/dev/plain",
            "file_count": 10,
            "folder_count": 3,
            "total_size_bytes": 4096,
            "mtime": "2026-04-27T18:00:00+00:00",
            "scanned_at": "2026-04-27T18:30:00+00:00",
        }


class TestFormatInspectJson:
    """Tests for format_inspect_json()."""

    def test_round_trips_through_json(self) -> None:
        scanned = datetime(2026, 4, 27, 18, 30, tzinfo=UTC)
        mtime = datetime(2026, 4, 27, 18, 0, tzinfo=UTC)
        result = NonGitInspectResult(
            path=Path("/dev/plain"),
            file_count=2,
            folder_count=1,
            total_size_bytes=99,
            mtime=mtime,
            scanned_at=scanned,
        )
        output = format_inspect_json(result)
        parsed = json.loads(output)

        assert parsed["kind"] == "non-git"
        assert parsed["file_count"] == 2
