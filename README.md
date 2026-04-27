# DevFolder - Project Overview

A CLI tool to scan and categorize local development projects.

## Quick Start

```sh
uv run devfolder scan                 # Scan current directory
uv run devfolder scan ~/dev           # Scan a specific directory
uv run devfolder inspect ~/dev/myrepo # Detailed data for one project
uv run devfolder report ~/dev         # Scan + inspect every project (single JSON)
```

## Project Structure

```
src/devfolder/
├── __init__.py      # Package entry point (re-exports `main`)
├── cli.py           # CLI dispatch and subcommand parsers
├── scanner.py       # Directory scanning logic
├── classifier.py    # Project classification
├── inspector.py     # Per-project detailed inspect
├── report.py        # Scan + inspect-all augmented document
├── git.py           # Git CLI wrappers
├── models.py        # Data classes and enums
├── output.py        # Text formatting (tree + inspect)
├── serializers.py   # JSON serialization
└── config.py        # Configuration loading
```

## Key Concepts

### Node Types
- **Project**: A folder containing `.git` or a leaf folder at depth 2
- **Category**: A folder at depth 1 that is not itself a project
- **Symlink**: A symbolic link (not followed)
- **Ignored**: Dotfolders or `node_modules`
- **Error**: Folders with permission errors

### Project Classifications
1. **Empty**: Project folder with no contents
2. **Local Untracked**: No `.git` folder
3. **Local Git**: Has `.git` but no remotes
4. **Personal Remote**: Remote URL contains configured username
5. **Other Remote**: Has remote(s) not matching username

## Configuration

Config file: `~/.config/devfolder/config.toml`

```toml
username = "ahejackson"
```

## Commands

```sh
uv run devfolder scan    # Run the tool
uv run pytest            # Run tests
uv run mypy src tests    # Type checking
uv run ruff check src tests  # Linting
```
