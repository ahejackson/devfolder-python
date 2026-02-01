## Summary

Added pytest as a dev dependency and created a test suite with 85 tests across 4 test modules:

- **tests/conftest.py** - Shared fixtures: directory structures (dev_folder, root_is_project, etc.), config
  objects, and a make_remote_patch context manager for mocking git remotes
- **tests/test_classifier.py** (29 tests) - URL matching across SSH/HTTPS/git formats with parametrize, empty/git
  directory detection, project classification for all 5 types, remote priority (origin first), and no-username
  edge case
- **tests/test_scanner.py** (17 tests) - should_ignore for dotfolders/node_modules, scan_category with mixed
  children, full scan with the two-level structure, symlinks, ignored nodes, category-level projects, sorting,
  and edge cases (empty root, files-only root)
- **tests/test_output.py** (20 tests) - Formatting for all project types and ignore reasons, node rendering for
  all 5 node kinds, tree connector characters (tee vs elbow), nested indentation with/without pipe, and full
  tree formatting
- **tests/test_config.py** (9 tests) - Config loading, missing/empty/invalid TOML handling, frozen immutability,
  and default path
