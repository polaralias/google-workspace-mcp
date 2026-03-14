# Configuration Reference

This guide explains the supported environment variables and deployment knobs for `google-workspace-mcp`.

## Required settings

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_WORKSPACE_MCP_API_KEY` | Recommended | none | Service-specific bearer token accepted by the HTTP MCP endpoint. |
| One Google auth source | Yes | none | At least one auth source must be available before most Google Workspace tools can succeed. |

Supported auth sources:
- Persisted OAuth credentials stored under `.oauth/` and pointed to by `GOOGLE_MCP_CREDENTIALS_DIR`.
- A service account via `GOOGLE_SERVICE_ACCOUNT_FILE` or `GOOGLE_SERVICE_ACCOUNT_JSON`.
- Google Keep master-token access via `GOOGLE_KEEP_EMAIL` and `GOOGLE_KEEP_MASTER_TOKEN`.
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
| `GOOGLE_SERVICE_ACCOUNT_FILE` | No | none | Path to a mounted service-account JSON file inside the container. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | No | none | Raw service-account JSON string as an alternative to a mounted file. |
| `GOOGLE_IMPERSONATED_USER` | No | none | Workspace user to impersonate when domain-wide delegation is enabled. |
| `GOOGLE_DEFAULT_USER_EMAIL` | No | none | Default user email applied when a tool call omits `user_google_email`. |

## Google Keep and public API settings

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_KEEP_EMAIL` | No | none | Google account email paired with the Keep master token. |
| `GOOGLE_KEEP_MASTER_TOKEN` | No | none | Master token used for Keep access without OAuth app registration. |
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

## Auth-mode guidance by tool family

- Calendar, Drive, Docs, Sheets, Slides, Gmail, Admin, Chat, Meet, and most Tasks operations generally require OAuth or a service account.
- Google Keep tools can use the existing individual-account master-token flow instead of OAuth app registration.
- API-key-only setups are intentionally limited and will not provide full Workspace coverage.

## Files and deployment notes

- The public tool surface is split across multiple `tool_manifest_google*.json` files and then merged at runtime.
- The bundled compose file assumes the external Docker network `reverse_proxy` already exists.
- Persist `.oauth/` as a mounted directory if you want to preserve existing OAuth credentials without reauth.
- Legacy Keep managed labels using `google-workspace-fast-mcp` remain accepted for note edits, so old note metadata continues to work after the rename.
