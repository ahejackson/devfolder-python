"""Tests for devfolder.report module."""

from pathlib import Path

from devfolder.config import Config
from devfolder.models import Owner
from devfolder.report import run_report

from .conftest import git_commit, init_git_repo


def _build_dev_tree(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create a small dev tree.

    Layout:
        root/
        ├── tools/
        │   ├── git-project/   (real git repo, with one commit)
        │   └── plain/         (untracked: 2 files, 1 subdir)
        └── empty-cat/
            └── (no children)

    Returns (root, git_project_path, plain_path, empty_cat).
    """
    root = tmp_path / "root"
    root.mkdir()

    tools = root / "tools"
    tools.mkdir()

    git_project = tools / "git-project"
    init_git_repo(git_project)
    (git_project / "main.py").write_text("print('hi')")
    git_commit(git_project, "initial")

    plain = tools / "plain"
    plain.mkdir()
    (plain / "a.txt").write_text("a")
    (plain / "b.txt").write_text("bb")
    (plain / "src").mkdir()
    (plain / "src" / "c.py").write_text("ccc")

    empty_cat = root / "empty-cat"
    empty_cat.mkdir()

    return root, git_project, plain, empty_cat


class TestRunReport:
    """Tests for the augmented document produced by run_report."""

    def test_augments_every_project_node(self, tmp_path: Path) -> None:
        root, git_project, plain, _ = _build_dev_tree(tmp_path)

        document = run_report(root, Config())

        # Locate the two project nodes
        children = document["children"]
        assert isinstance(children, list)
        tools_cat = next(c for c in children if c["name"] == "tools")
        assert isinstance(tools_cat, dict)
        tool_children = tools_cat["children"]
        assert isinstance(tool_children, list)
        by_name = {c["name"]: c for c in tool_children}

        git_node = by_name["git-project"]
        assert isinstance(git_node, dict)
        assert git_node["kind"] == "project"
        assert "inspect" in git_node
        inspect = git_node["inspect"]
        assert isinstance(inspect, dict)
        assert inspect["kind"] == "git"
        assert inspect["working_tree"]["clean"] is True
        assert inspect["branches"]["total"] == 1

        plain_node = by_name["plain"]
        assert isinstance(plain_node, dict)
        assert plain_node["kind"] == "project"
        plain_inspect = plain_node["inspect"]
        assert isinstance(plain_inspect, dict)
        assert plain_inspect["kind"] == "non-git"
        assert plain_inspect["file_count"] == 3
        assert plain_inspect["folder_count"] == 1

    def test_categories_have_no_inspect_field(self, tmp_path: Path) -> None:
        root, _, _, _ = _build_dev_tree(tmp_path)

        document = run_report(root, Config())

        children = document["children"]
        assert isinstance(children, list)
        tools_cat = next(c for c in children if c["name"] == "tools")
        assert "inspect" not in tools_cat

    def test_progress_callback_fires_in_order(self, tmp_path: Path) -> None:
        root, git_project, plain, _ = _build_dev_tree(tmp_path)
        events: list[tuple[int, int, Path]] = []

        run_report(
            root,
            Config(),
            on_progress=lambda i, total, p: events.append((i, total, p)),
        )

        # 2 projects total: git-project and plain
        assert len(events) == 2
        assert all(total == 2 for _, total, _ in events)
        # 1-based indices, in encounter order
        indices = [i for i, _, _ in events]
        assert indices == [1, 2]
        # Both project paths covered
        seen_paths = {p for _, _, p in events}
        assert seen_paths == {git_project, plain}

    def test_root_project_is_inspected(self, tmp_path: Path) -> None:
        """When the scan target itself is a project, it gets inspect data."""
        root = tmp_path / "solo"
        init_git_repo(root)
        (root / "main.py").write_text("hi")
        git_commit(root)

        events: list[Path] = []
        document = run_report(
            root, Config(), on_progress=lambda i, t, p: events.append(p)
        )

        assert document["is_root_project"] is True
        root_project = document["root_project"]
        assert isinstance(root_project, dict)
        assert "inspect" in root_project
        assert events == [root]

    def test_uses_config_for_owner_matching(self, tmp_path: Path) -> None:
        """Owner classification still works through report."""
        root = tmp_path / "root"
        root.mkdir()
        cat = root / "tools"
        cat.mkdir()
        repo = cat / "myrepo"
        init_git_repo(repo)
        (repo / "a.txt").write_text("a")
        git_commit(repo)
        # Add a configured-owner remote
        from .conftest import run_git as _run_git

        _run_git(
            repo,
            "remote",
            "add",
            "origin",
            "git@github.com:testuser/myrepo.git",
        )

        config = Config(owners=(Owner(name="testuser", host="github.com"),))
        document = run_report(root, config)

        children = document["children"]
        assert isinstance(children, list)
        tools = children[0]
        assert isinstance(tools, dict)
        myrepo = tools["children"][0]
        assert isinstance(myrepo, dict)
        assert myrepo["project_type"] == "owned-remote"
        assert myrepo["owner"] == "testuser"
