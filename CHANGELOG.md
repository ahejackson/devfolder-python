# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-04-27

### Added
- Recognise bare git repositories as projects. Bare layouts (project directory containing `HEAD` + `objects/` + `refs/`) are detected at any level of a scan and classified by remote like any other git project.
- `git_layout` field on project nodes in JSON output: `working-tree`, `linked` (worktrees / submodules), `bare`, or `null` for non-git projects. Visible in scan output without needing to call inspect.
- New `bare-git` inspect kind for bare repositories. Shape mirrors the existing `git` kind minus `working_tree` (which doesn't apply without a working tree).
- `gitdir` field on the `git` inspect kind: absolute path of this checkout's git directory.
- `linked_to` field on the `git` inspect kind: tagged union (`worktree` / `submodule`) describing the linked repo when the checkout is a worktree or submodule. `null` for plain working-tree projects.

### Fixed
- Worktrees and submodules (which use a `.git` *file* containing a `gitdir:` pointer) were misclassified as `local-untracked`. They are now correctly recognised as git projects, with `git_layout: "linked"` and a populated `linked_to` on the inspect side.

### Schema changes
- **GUI / JSON consumers should update.** Three additive changes: a new `git_layout` field on project nodes, a new `bare-git` inspect kind, and two new fields (`gitdir`, `linked_to`) on the existing `git` inspect kind. See [`docs/json-output.md`](docs/json-output.md) for the full reference.

## [0.4.0] - 2026-04-27

### Added
- `devfolder report <root>` subcommand. Scans a directory tree and runs `inspect` on every project, emitting a single augmented JSON document (the scan output with each project node carrying its inspect record). Progress lines (`Inspecting project N of M: <path>`) are written to stderr; the JSON document is written to a file (default: `report.json` in CWD; override with `-f`). Built for the salvage-laptop use case — one sweep that surfaces unpushed work, untracked branches, recent activity, and disk usage across an entire dev folder.

## [0.3.0] - 2026-04-27

### Added
- `devfolder inspect <path>` subcommand. Collects detailed per-project data for a single project: working tree state, branch summary, stash count, last commit, filesystem mtime, and parsed remotes for git projects; or file count, folder count, total size on disk, and mtime for non-git projects. Default text output for human use; `-o json` emits a structured record with a `kind: "git" | "non-git"` discriminator.
- `git.py` module centralising git CLI invocations (`status`, `branches`, `stash_count`, `last_commit_at`, `parse_remote`, `get_git_remotes`).

### Changed
- **Breaking:** CLI restructured around subcommands. The previous bare invocation (`devfolder ~/dev`) is replaced with `devfolder scan ~/dev`. Run `devfolder --help` to see available subcommands.

### Notes
- Non-git inspect walks skip `node_modules`, `.git`, and `.venv` directories. Other build/cache directories (`dist`, `target`, `__pycache__`, etc.) are walked.

## [0.2.1] - 2026-04-26

### Added
- `generated_at` field on JSON output, holding an ISO 8601 UTC timestamp of when the scan was produced. Makes it easier to identify and diff successive output files.

### Fixed
- Misconfigured config files now produce warnings instead of being silently ignored. Unknown top-level keys (e.g. the pre-0.2.0 `username` key) are flagged, and a config file that yields zero owners produces a 'no [[owners]] configured' warning. A missing config file remains silent.

## [0.2.0] - 2026-04-26

### Added
- `--version` flag prints `devfolder <version>` and exits.
- `owner` field on project records, holding the matched owner name (from the configured `owners` list).
- Owner appears inline in tree output: `[owned-remote: <name>]`.

### Changed
- **BREAKING**: Replaced the `username` config field with an `owners` array of tables. Each entry has a `name` and `host`. Multiple owners across multiple hosts are now supported (e.g. personal GitHub account + GitHub orgs + a historical GitLab account).
- **BREAKING**: Renamed project type `personal-remote` → `owned-remote`. Affects both tree output and JSON serialization.
- Owner matching now requires both host and name to match strictly. Previously a name match on any host would classify as personal-remote.

### Migration
Replace `username = "yourname"` in `~/.config/devfolder/config.toml` with:

```toml
[[owners]]
name = "yourname"
host = "github.com"
```

## [0.1.0] - 2026-04-26

### Added
- Initial CLI: scan a directory tree, classify projects by git status, and output a tree view.
- Project classifications: `EMPTY`, `LOCAL_UNTRACKED`, `LOCAL_GIT`, `PERSONAL_REMOTE`, `OTHER_REMOTE`.
- Configuration via `~/.config/devfolder/config.toml` (`username` field).
- JSON output format (`-o json`) and file output (`-f <path>`).
- Support for nested project categories (one level deep).
- Pytest test suite covering classifier, scanner, output, and CLI.
