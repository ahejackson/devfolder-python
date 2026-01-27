# 01 - Implementation Plan

## Overview

Build a proof-of-concept CLI tool that scans a directory tree, identifies development projects, classifies them by git status, and outputs a tree view.

## Architecture

### Module Structure

```
src/devfolder_python/
├── __init__.py      # CLI entry point with main()
├── models.py        # Data classes and enums
├── config.py        # Configuration loading
├── scanner.py       # Directory scanning
├── classifier.py    # Project classification
└── output.py        # Tree view formatting
```

### Data Models

```python
# Enums
class NodeKind(Enum):
    PROJECT = "project"
    CATEGORY = "category"
    SYMLINK = "symlink"
    IGNORED = "ignored"
    ERROR = "error"

class ProjectType(Enum):
    EMPTY = "empty"
    LOCAL_UNTRACKED = "local-untracked"
    LOCAL_GIT = "local-git"
    PERSONAL_REMOTE = "personal-remote"
    OTHER_REMOTE = "other-remote"

# Data classes
@dataclass
class Node:
    name: str
    path: Path
    kind: NodeKind

@dataclass
class ProjectNode(Node):
    project_type: ProjectType
    remote_url: str | None = None

@dataclass
class CategoryNode(Node):
    children: list[Node]
    is_empty: bool = False

@dataclass
class SymlinkNode(Node):
    target: Path

@dataclass
class ErrorNode(Node):
    error_message: str

@dataclass
class ScanResult:
    root: Path
    children: list[Node]
    is_project: bool  # True if root itself is a project
```

### Scanning Algorithm

```
scan(root):
    if root has .git:
        return ScanResult(root, [], is_project=True)

    children = []
    for entry in root:
        if is_symlink(entry):
            children.append(SymlinkNode)
        elif is_dotfolder(entry) or is_node_modules(entry):
            children.append(IgnoredNode)
        elif is_directory(entry):
            if has_permission_error(entry):
                children.append(ErrorNode)
            elif has_git(entry):
                children.append(ProjectNode)  # category-level project
            else:
                # This is a category - scan its children
                category_children = scan_category(entry)
                children.append(CategoryNode with category_children)

    return ScanResult(root, children, is_project=False)

scan_category(category_path):
    children = []
    for entry in category_path:
        if is_symlink(entry):
            children.append(SymlinkNode)
        elif is_dotfolder(entry) or is_node_modules(entry):
            children.append(IgnoredNode)
        elif is_directory(entry):
            if has_permission_error(entry):
                children.append(ErrorNode)
            else:
                children.append(ProjectNode)  # classify it
    return children
```

### Classification Logic

```
classify_project(path):
    if is_empty(path):
        return EMPTY

    if not has_git(path):
        return LOCAL_UNTRACKED

    remotes = get_git_remotes(path)
    if not remotes:
        return LOCAL_GIT

    # Check origin first, then first available
    remote_url = remotes.get("origin") or next(iter(remotes.values()))

    if username_in_url(remote_url, config.username):
        return PERSONAL_REMOTE
    else:
        return OTHER_REMOTE
```

### Configuration

Config file location: `~/.config/devfolder/config.toml`

```toml
username = "ahejackson"
```

Uses Python's `tomllib` (stdlib in 3.11+) for parsing.

### Output Format

Tree-style output using box-drawing characters:

```
~/dev
├── tools/
│   ├── devfolder [personal-remote] git@github.com:ahejackson/devfolder.git
│   └── scripts [local-git]
├── work/
│   ├── project-a [other-remote] git@github.com:company/project-a.git
│   └── project-b [local-untracked]
├── experiments/  [empty]
├── .config/  [ignored: dotfolder]
└── old-project -> /archive/old  [symlink]
```

## Implementation Order

1. **models.py** - Define all data structures
2. **config.py** - Configuration loading with defaults
3. **classifier.py** - Git remote detection and classification
4. **scanner.py** - Directory scanning
5. **output.py** - Tree view formatting
6. **__init__.py** - CLI entry point
7. **Tests** - Basic test coverage

## Dependencies

- `tomllib` - Config parsing (stdlib 3.11+)
- `pathlib` - Path handling (stdlib)
- `argparse` - CLI parsing (stdlib)

No external dependencies needed for the PoC.

## Edge Cases Handled

- Root is itself a project (has .git)
- Category-level folder has .git (treat as project)
- Symlinks (record but don't follow)
- Dotfolders and node_modules (mark as ignored)
- Permission errors (record error message)
- Empty categories (mark as empty)
- Empty projects (new classification)
- Multiple git remotes (check origin first)
- Non-GitHub remotes (check username in any URL)

## Python Version

- Target: Python 3.14
- Minimum: Python 3.13
- Uses: match statements, modern type hints, tomllib
