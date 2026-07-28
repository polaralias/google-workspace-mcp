---
type: "Architecture Concept"
title: "Architecture"
description: "Documents Architecture for the google-workspace-mcp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - google-workspace-mcp
  - architecture-concept
navigation:
  role: foundational
  order: 20
---
# Architecture

## System Shape

`google-workspace-mcp` is a standalone FastMCP server with direct HTTP transport.

Runtime flow:

1. `tool_manifest_google*.json` files define the public tool interface.
2. `manifest_support.load_manifest(...)` merges those manifests.
3. `server.py` registers one FastMCP tool per manifest entry.
4. Every call routes through `GoogleRuntime.dispatch(...)`.
5. Domain dispatchers execute Google Workspace or Keep-specific behaviour.

## Main Components

- `server.py`
  - process bootstrap
  - health routes
  - Google auth selection
  - Keep master-token backend lifecycle
  - top-level dispatch
- `auth_support.py`
  - MCP bearer-token auth
  - OAuth credential loading
  - runtime env parsing
- `calendar_dispatch.py`
  - calendar events
  - free/busy
  - calendar ACL rules
- `drive_dispatch.py`
  - Drive search, folder lifecycle, file create/read/delete, permissions
- `docs_dispatch.py`
  - Google Docs create/read/update
- `gmail_dispatch.py`
  - Gmail search and filter lifecycle
- `sheets_dispatch.py`
  - Sheets values read/write flows
- `slides_dispatch.py`
  - Slides create/read/add-slide and public PDF export
- `tasks_dispatch.py`
  - task list and task lifecycle
- `contacts_dispatch.py`
  - contacts CRUD and bounded search
- `forms_dispatch.py`
  - Forms batch update
- `meet_dispatch.py`
  - Meet conference record reads
- `keep_dispatch.py`
  - Keep note CRUD and label listing through master token
- `tool_support.py`
  - per-tool support metadata and generated support matrix rendering

## Auth Boundaries

There are two auth layers:

- MCP client auth
  - static bearer-token validation for the MCP endpoint
- Google auth
  - stored OAuth for user-scoped Workspace operations
  - API key for the narrow documented public-read subset
  - Keep master token for Keep-only workflows

## Product Boundary

- The public manifests now contain only tools with current support evidence.
- Unsupported or previously exploratory wrappers remain internal implementation detail until they are reintroduced with verification.
- `uv run` is the supported local runtime path.

## Canonical Docs

- [README.md](README.md)
- [docs/configuration.md](docs/configuration.md)
- [docs/product-specs/support-matrix.md](docs/product-specs/support-matrix.md)
- [docs/generated/tool-support-matrix.md](docs/generated/tool-support-matrix.md)
- [docs/product-specs/auth-models.md](docs/product-specs/auth-models.md)
- [docs/RELIABILITY.md](docs/RELIABILITY.md)

## Repository knowledge

- [Documentation map](docs/knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
