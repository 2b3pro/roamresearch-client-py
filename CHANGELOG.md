# Changelog

## 0.3.5 - 2025-12-30

- feat(formatter): hierarchical markdown output preserving Roam's block structure
- feat(formatter): reference resolution with `--level` flag (default 1, 0 to disable)
- feat(cli): add `--level` / `-l` to control ref resolution depth (fetches external refs when > 1)
- feat(cli): add `--flat` flag for backwards-compatible flattened output
- feat(mcp): server now uses hierarchical formatting by default

## 0.3.4 - 2025-12-29

- fix(mcp): handle empty identifier list in handle_get
- feat(mcp): enhance search syntax and batch operations

## 0.3.3 - 2025-12-29

- fix(cli): exit code and refs lookup improvements
- fix(mcp): auto-create topic node if not exists
- docs: rewrite README
- feat(cli): unify save/update, add search enhancements

## 0.3.2 - 2025-12-29

- chore: update pdm scripts for server start and add test command
- fix: improve tag matching to handle end-of-string and prevent false positives
- ci: added compileall check
- test: add unit tests for search functions
- feat: add tag search, block references, and TODO search

