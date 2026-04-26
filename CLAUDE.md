# DevFolder - Project Overview

A CLI tool to scan and categorize local development projects.


## Instructions
- Follow the Python code style guidelines in `@/docs/CODING-STYLE.md
- Use `uv` to install any dependencies, not `pip`.
- Support python 3.13 and up


## Quick Start

```bash
uv run devfolder scan              # Scan current directory
uv run devfolder scan ~/dev        # Scan specific directory
uv run devfolder scan ~/dev -o json          # Write JSON to devfolder.json in CWD
uv run devfolder scan ~/dev -o json -f out.json  # Write JSON to specific file
uv run devfolder scan ~/dev -f tree.txt      # Write text output to file
```


## Project Structure

```
src/devfolder/
├── __init__.py      # Package entry point (re-exports `main`)
├── cli.py           # CLI dispatch and subcommand parsers
├── scanner.py       # Directory scanning logic
├── models.py        # Data classes and enums
├── classifier.py    # Project classification
├── output.py        # Tree view formatting
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
4. **Owned Remote**: Remote URL matches a configured owner (host + name)
5. **Other Remote**: Has remote(s) not matching any configured owner


## Configuration

Config file: `~/.config/devfolder/config.toml`

```toml
[[owners]]
name = "ahejackson"
host = "github.com"

[[owners]]
name = "my-org"
host = "github.com"
```

Each owner is a `(host, name)` pair. Strict matching: both must match for a remote to count as owned.


## Commands

```bash
uv run devfolder scan    # Run the tool
uv run pytest            # Run tests
uv run mypy src tests    # Type checking
uv run ruff check src tests  # Linting
```
