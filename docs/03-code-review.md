# 03 - Code Review

## Overall Assessment

The codebase is clean, well-structured, and does what it sets out to do. Module responsibilities are clear, the data model is sensible, and test coverage is solid. The issues below are mostly about robustness and maintainability rather than correctness.

---

## Bugs

### 1. `format_ignore_reason` has no exhaustive match (output.py:44-48) — FIXED

The `match` statement covers both `IgnoreReason` variants, but has no fallback. If a new variant is added to the enum, this function will silently return `None` (implicit return), which will cause a `TypeError` downstream when it's interpolated into an f-string. This is the only `match` in the codebase without a catch-all — `format_node` is protected by the `assert isinstance()` calls.

**Resolution:** Added a `case _:` default that raises `ValueError`, so adding a new `IgnoreReason` variant without updating the formatter will fail immediately.

### 2. `classify_project` misclassifies `.git` worktrees (classifier.py:94-103) — DEFERRED

`has_git_directory` checks for `.git` being a *directory*. Git worktrees and submodules use a `.git` *file* (containing `gitdir: /path/to/...`). These projects will be classified as `LOCAL_UNTRACKED` instead of being recognised as git repositories. The existing test `test_git_file_not_dir` documents this as intentional, but it's worth noting this will produce incorrect results for anyone using worktrees.

**Status:** Not urgent for a PoC, but worth tracking. Detecting `.git` as a file and reading the `gitdir` reference would handle both cases.

### 3. `remotes.get("origin") or next(...)` has a subtle bug (classifier.py:134) — FIXED

If `origin` exists but has an empty string URL (`""`), the `or` will skip it and fall through to the next remote. This is unlikely in practice but technically incorrect — `get` + `or` conflates "missing" with "falsy".

**Resolution:** Changed to `if "origin" in remotes: ... else: ...` to correctly distinguish missing from falsy.

---

## Code Structure

### 4. Duplicated error handling blocks in scanner.py — FIXED

The `PermissionError` / `OSError` handler pattern was repeated six times across `scan` and `scan_category`. Each block created an `ErrorNode` with the same shape.

**Resolution:** Extracted `_make_error_node(entry, error)` helper. Also consolidated separate `PermissionError` / `OSError` handlers into single `OSError` catches (since `PermissionError` is a subclass of `OSError`).

### 5. Duplicated symlink handling in scanner.py — FIXED

The symlink-to-directory check block was identical between `scan` and `scan_category`.

**Resolution:** Extracted `_try_symlink_node(entry) -> SymlinkNode | None` helper used in both functions.

### 6. `NodeKind` enum is redundant with the class hierarchy (models.py) — DEFERRED

Each `Node` subclass has a fixed `kind` value set in `__init__`, so `node.kind` is always derivable from `type(node)`. The `format_node` function matches on `node.kind` then immediately `assert isinstance(...)` — doing the same discrimination twice. The `kind` field serves as a parallel type system.

**Status:** This works fine as-is and the `kind` field could be useful for serialisation later. But if more node types are added, consider whether `isinstance` checks alone would be simpler. Alternatively, a visitor pattern or `singledispatch` would eliminate both the enum and the assertions.

### 7. Manual `__init__` methods on frozen dataclasses (models.py) — DEFERRED

Every `Node` subclass has a hand-written `__init__` using `object.__setattr__` to work around frozen dataclass inheritance. This is a known pain point with frozen dataclass hierarchies in Python. It works, but it's boilerplate-heavy and easy to get wrong when adding fields.

**Status:** Fine for now. If the model grows, consider using `kw_only=True` on the base class (Python 3.10+) which can simplify frozen inheritance, or switching to `attrs` which handles this more gracefully.

---

## Robustness

### 8. `config.load` silently swallows all errors (config.py:34-38) — FIXED

If the config file exists but contains valid TOML with an unexpected type for `username` (e.g. `username = 42`), it will be silently accepted and `Config.username` will be an `int` at runtime despite the `str | None` annotation.

**Resolution:** Added an `isinstance(username, str)` check after reading from TOML. Non-string values now fall back to defaults. Added a corresponding test (`test_load_non_string_username_returns_defaults`).

### 9. No `__all__` exports in most modules — FIXED

The coding style guide says to "define `__all__` in modules to explicitly declare public API". Only `__init__.py` had one.

**Resolution:** Added `__all__` to all five source modules: `models.py`, `config.py`, `classifier.py`, `scanner.py`, and `output.py`.

---

## Output

### 10. `~` home directory shortening (output.py) — DEFERRED

When scanning `~/Dev`, the output shows the full resolved path (`/Users/adamjackson/Dev/`). Most tree-style tools shorten this to `~/Dev/` for readability.

**Status:** Nice-to-have for a future iteration.

### 11. Trailing slash inconsistency in output — FIXED

Projects and categories get a trailing `/` but symlinks didn't. Symlinks to directories are conceptually directories too.

**Resolution:** Added `/` after the symlink name in the output for consistency.

---

## Tests

### 12. `conftest.py` fixtures could use `pytest.fixture` scope — FIXED

Fixtures like `config` and `config_no_username` are stateless frozen dataclasses — they were being recreated for every test unnecessarily.

**Resolution:** Set `scope="session"` on both `config` and `config_no_username` fixtures.

### 13. Missing test for `get_git_remotes` parsing — FIXED

The `get_git_remotes` function parses `git remote -v` output, but there were no direct tests for this parsing logic. It was only tested indirectly through `classify_project` with mocking.

**Resolution:** Added `TestGetGitRemotes` class with 7 tests covering: single remote, multiple remotes, fetch-over-push preference, empty output, nonzero return code, subprocess error, and OS error.

### 14. No integration test for `main()` — FIXED

The CLI entry point was untested.

**Resolution:** Added `tests/test_main.py` with 5 tests covering: scanning a directory, scanning a root project, nonexistent path exit, file path exit, and default root behaviour.

---

## Summary

| Status | Item | Resolution |
|--------|------|------------|
| FIXED | #1 Non-exhaustive match in `format_ignore_reason` | Added `case _: raise ValueError` |
| FIXED | #3 `or` vs `in` for origin remote lookup | Changed to `if "origin" in remotes` |
| FIXED | #4 Duplicated error handling in scanner | Extracted `_make_error_node` helper |
| FIXED | #5 Duplicated symlink handling in scanner | Extracted `_try_symlink_node` helper |
| FIXED | #8 Config type validation | Added `isinstance` check |
| FIXED | #9 Missing `__all__` exports | Added to all source modules |
| FIXED | #11 Trailing slash on symlinks | Added `/` to symlink output |
| FIXED | #12 Session-scoped fixtures | Set `scope="session"` |
| FIXED | #13 `get_git_remotes` parsing tests | 7 new tests |
| FIXED | #14 `main()` integration tests | 5 new tests |
| DEFERRED | #2 `.git` file (worktree) support | Future enhancement |
| DEFERRED | #6 NodeKind redundancy | Design decision for later |
| DEFERRED | #7 Manual `__init__` boilerplate | Revisit if model grows |
| DEFERRED | #10 Home directory shortening | Nice-to-have |

Test count increased from 88 to 101 (13 new tests). All pass, ruff clean, mypy strict clean.
