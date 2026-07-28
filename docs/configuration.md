---
type: "Reference"
title: "Configuration Reference"
description: "Documents Configuration Reference for the google-workspace-mcp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - google-workspace-mcp
  - reference
navigation:
  role: reference
  order: 200
---
# Configuration Reference

This guide describes the supported runtime and deployment settings for `google-workspace-mcp`.

Support status is defined in [product-specs/support-matrix.md](docs\product-specs\support-matrix.md) and [generated/tool-support-matrix.md](docs\generated\tool-support-matrix.md). The manifest files and this configuration guide describe the public server surface; they are kept aligned with the verified product contract.

## Required settings

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_WORKSPACE_MCP_API_KEY` | Recommended | none | Service-specific bearer token accepted by the HTTP MCP endpoint. |
| One Google auth source | Yes | none | At least one auth source must be available before most Google Workspace tools can succeed. |

Supported Google auth sources:
- Persisted OAuth credentials stored under `.oauth/` and pointed to by `GOOGLE_MCP_CREDENTIALS_DIR`.
- Unofficial Google Keep master-token access via `GOOGLE_KEEP_EMAIL` and `GOOGLE_KEEP_MASTER_TOKEN`.
- `GOOGLE_API_KEY` for the smaller subset of public-data and enrichment-style requests that support API-key auth.

## MCP client auth

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MCP_API_KEY` | No | none | Generic single-key alias if you prefer a shared naming pattern across services. |
| `MCP_API_KEYS` | No | none | Comma-separated additional bearer tokens accepted by the MCP endpoint. |
| `API_KEY_MODE` | No | static auth enabled | Set to `disabled` to turn off bearer-token checks entirely. |

## OAuth and credentials

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_MCP_CREDENTIALS_DIR` | No | `/app/.oauth` in compose examples | Directory where the server loads and stores persisted OAuth credentials. |
| `GOOGLE_OAUTH_CLIENT_ID` | No | none | Client ID used by the helper OAuth flow. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | No | none | Client secret used by the helper OAuth flow. |
| `GOOGLE_DEFAULT_USER_EMAIL` | No | none | Default user email applied when a tool call omits `user_google_email`. |

## Google Keep and public API settings

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_KEEP_EMAIL` | No | none | Google account email paired with the Keep master token. |
| `GOOGLE_KEEP_MASTER_TOKEN` | No | none | Master token used for the repository's supported Keep path. |
| `GOOGLE_KEEP_MANAGED_LABEL` | No | `google-workspace-mcp` | Label used to identify notes managed by this server. |
| `GOOGLE_KEEP_UNSAFE_MODE` | No | `false` | Enables less restrictive Keep operations where supported. |
| `GOOGLE_API_KEY` | No | none | Google API key used by tools that support key-based access. |
| `MASTER_KEY` | No | none | Legacy decryption helper for older encrypted credential/state flows. |

## Endpoint and transport

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_WORKSPACE_MCP_PORT` | No | `3002` | Internal service port used by the compose examples. |
| `GOOGLE_WORKSPACE_MCP_HOST_PORT` | No | `3002` | Host-side published port in the bundled `docker-compose.yml`. |
| `GOOGLE_WORKSPACE_MCP_PATH` | No | `/mcp` | HTTP path where the MCP endpoint is exposed. |
| `MCP_HOST` / `HOST` | No | `127.0.0.1` locally, `0.0.0.0` in compose | Host bind address used by `scripts/run_server.py` and FastMCP. |
| `MCP_PORT` / `PORT` | No | `3002` | Generic runtime port override. |
| `MCP_PATH` | No | `/mcp` | Generic runtime path override. |
| `MCP_TRANSPORT` / `FASTMCP_TRANSPORT` | No | `streamable-http` | Transport mode. `stdio` is mainly useful for local tooling and testing. |

## Auth-Mode Guidance

- OAuth is the primary path for Calendar, Drive, Docs, Sheets, Slides, Gmail, Tasks, Contacts, Forms, and Meet.
- Google Keep support is master-token-only. There is no supported OAuth-backed Keep story.
- API-key-only setups are intentionally narrow and should be limited to the documented public-read subset.

## Files and deployment notes

- The public tool surface is split across multiple `tool_manifest_google*.json` files and then merged at runtime.
- The bundled compose file is self-contained by default, does not require a pre-created external Docker network, and can start without a repo-local `.env` file.
- Persist `.oauth/` as a mounted directory if you want to preserve existing OAuth credentials without reauth.
- Legacy Keep managed labels using `google-workspace-fast-mcp` remain accepted for note edits, so old note metadata continues to work after the rename.

## Verification Commands

- Default non-live suite: `uv run python -m unittest`
- Opt-in live suite: set `GOOGLE_WORKSPACE_MCP_RUN_LIVE_TESTS=true`, then run `uv run python -m unittest discover tests -p "test_live_*_contract.py"`
- Opt-in Docker smoke: set `GOOGLE_WORKSPACE_MCP_RUN_DOCKER_TESTS=true`, then run `uv run python -m unittest tests.test_docker_contract`

## Repository knowledge

- [Documentation map](knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
