# DevFolder - Project Overview

A CLI tool to scan and categorize local development projects.

## Instructions
- Follow the Python code style guidelines in`@/docs/CODING-STYLE.md`
- Use the `docs` folder to save markdown documents about the current state of the project, such as a "scratchpad"
- Write all major progress reports as markdown files as well as outputting them to the console.
- Progress report filenames should start with a zero-padded two digit number that increases sequentially to keep things organised - for example `01-plan.md`
- Use `uv` to install any dependencies, not `pip`.
- Support python 3.13 and up

## Quick Start

```bash
uv run devfolder              # Scan current directory
uv run devfolder ~/dev        # Scan specific directory
```

## Project Structure

```
src/devfolder/
├── __init__.py      # CLI entry point
├── scanner.py       # Directory scanning logic
├── models.py        # Data classes and enums
├── classifier.py    # Project classification
├── output.py        # Tree view formatting
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
uv run mypy src          # Type checking
uv run ruff check src    # Linting
```

## Future Considerations

- [ ] Option to list all remotes for a project
- [ ] Separate usernames per git service (GitHub, GitLab, etc.)
- [ ] Option to include bare git repositories
- [ ] Flag to include/exclude dotfolders
- [ ] More sophisticated ignore patterns
- [ ] Git operations: fetch, push, pull
- [ ] Alternative output formats (JSON, etc.)
