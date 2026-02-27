# DevFolder - Project Overview

A CLI tool to scan and categorize local development projects.


## Issue Tracking

This project uses **bd (beads)** for issue tracking. Run `bd prime` for workflow context.

**Quick reference:**
- `bd ready` - Find unblocked work
- `bd create "Title" --type task --priority 2` - Create issue
- `bd close <id>` - Complete work
- `bd sync` - Sync with git (run at session end)


## Instructions
- Follow the Python code style guidelines in `@/docs/CODING-STYLE.md
- Use `uv` to install any dependencies, not `pip`.
- Support python 3.13 and up


## Quick Start

```bash
uv run devfolder              # Scan current directory
uv run devfolder ~/dev        # Scan specific directory
uv run devfolder ~/dev -o json          # Write JSON to devfolder.json in CWD
uv run devfolder ~/dev -o json -f out.json  # Write JSON to specific file
uv run devfolder ~/dev -f tree.txt      # Write text output to file
```


## Project Structure

```
src/devfolder/
├── __init__.py      # CLI entry point
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
4. **Personal Remote**: Remote URL contains configured username
5. **Other Remote**: Has remote(s) not matching username


## Configuration

Config file: `~/.config/devfolder/config.toml`

```toml
username = "ahejackson"
```


## Commands

```bash
uv run devfolder         # Run the tool
uv run pytest            # Run tests
uv run mypy src tests    # Type checking
uv run ruff check src tests  # Linting
```


## Future Considerations

- [ ] Option to list all remotes for a project
- [ ] Separate usernames per git service (GitHub, GitLab, etc.)
- [ ] Option to include bare git repositories
- [ ] Flag to include/exclude dotfolders
- [ ] More sophisticated ignore patterns
- [ ] Git operations: fetch, push, pull
- [x] Alternative output formats (JSON, etc.)
