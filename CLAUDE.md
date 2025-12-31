# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python SDK + CLI + MCP Server for Roam Research. Provides programmatic access to Roam graphs with smart diff that preserves block UIDs across updates.

## Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_diff.py

# Run specific test
pytest tests/test_diff.py::test_match_blocks_single_level -v

# Start MCP server (for development)
python -m roamresearch_client_py.server

# CLI commands (after install)
rr get "Page Title"
rr search "keyword" --tag "#TODO"
rr save -t "Page" -f content.md
```

## Architecture

### Three-Tier Design

1. **SDK Client** (`client.py`) - Async HTTP client wrapping Roam Research API. Context manager pattern: `async with RoamClient() as client:`

2. **CLI** (`cli.py`) - User-facing command interface via `rr` command. Routes to async handlers.

3. **MCP Server** (`server.py`) - FastMCP server exposing tools for Claude/LLM integration. Includes background task queue with SQLite persistence.

### Core Modules

| Module | Purpose |
|--------|---------|
| `diff.py` | Smart diff algorithm matching blocks by content similarity, preserves UIDs |
| `gfm_to_roam.py` | GFM markdown → Roam Block structures using mistune AST |
| `formatter.py` | Roam blocks → Markdown output with block reference handling |
| `structs.py` | `Block` and `BlockRef` data structures |
| `config.py` | Config file management (`~/.config/roamresearch-client-py/config.toml`) |

### Smart Diff Flow (Key Feature)

The update workflow preserves references by matching existing blocks:

```
1. Fetch existing page → parse_existing_blocks()
2. Parse new markdown → gfm_to_blocks()
3. Match by similarity → diff_block_trees()
4. Generate actions → generate_batch_actions()
5. Execute atomically → batch_actions()
```

### Query Building

`client.py` contains pure functions for building Datalog queries:
- `make_block_conditions()`, `make_page_conditions()` for query construction
- Tag normalization strips `#`, `[[`, `]]` syntax
- HTML escaping for query strings

### Batch Operations

Actions are atomic (all-or-nothing). Action types: `create-page`, `create-block`, `update-block`, `move-block`, `delete-block`. Helper functions: `create_page()`, `create_block()`, `update_block()`, `move_block()`, `remove_block()`.

## Configuration

Environment variables take precedence over config file:
- `ROAM_API_TOKEN` - API token
- `ROAM_API_GRAPH` - Graph name

Config path: `~/.config/roamresearch-client-py/config.toml`

## Testing

Tests focus on the diff algorithm correctness:
- `test_diff.py` - Basic matching scenarios
- `test_diff_extreme.py` - Complex cases (parent deletion, UID preservation)
- `test_search.py` - Query parsing and search functions
- `test_verify.py` - Post-update verification
