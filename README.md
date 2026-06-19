<p align="center">
  <img src="Google%20Workspace%20MCP.png" alt="Google Workspace MCP banner" width="960" />
</p>

# Google Workspace MCP

Google Workspace MCP is a standalone FastMCP server for Google Workspace workflows, with optional Google Keep support through the documented master-token path.

## What It Does

The server exposes a verified subset of Google Workspace and Keep operations through an MCP interface so agents can work against email, calendar, Drive, and related Google surfaces without custom wrappers in every repo.

## Core Capabilities

- Google Workspace tool surface with checked support evidence
- OAuth-based access for the main Google Workspace flows
- limited API-key public-read compatibility path
- Google Keep access through the documented master-token workflow
- MCP and health endpoints for local or containerized runtime

## Endpoints

- MCP: `http://localhost:3002/mcp`
- Health: `http://localhost:3002/health`

## Supported Authentication

- `GOOGLE_WORKSPACE_MCP_API_KEY`, `MCP_API_KEY`, or `MCP_API_KEYS`
- stored OAuth credentials in `.oauth/` or `GOOGLE_MCP_CREDENTIALS_DIR`
- `GOOGLE_API_KEY` for the supported public-read subset
- `GOOGLE_KEEP_EMAIL` plus `GOOGLE_KEEP_MASTER_TOKEN` for Keep-only flows
- MCP auth defaults to required; set `API_KEY_MODE=disabled` only for intentional no-auth use.

## Quick Start

```bash
uv run python scripts/run_server.py serve
uv run python scripts/run_server.py doctor
uv run python scripts/run_server.py url
```

Helper flows:

```bash
npm run google:oauth
npm run google:keep-master-token
```

## Docker

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

## Verification

Default contract suite:

```bash
uv run python -m unittest discover -s tests -v
```

## Documentation

Start with:

- [docs/configuration.md](docs/configuration.md)
- [docs/tool-reference.md](docs/tool-reference.md)
- [docs/product-specs/support-matrix.md](docs/product-specs/support-matrix.md)

For repository workflow and agent-focused context, read [AGENTS.md](AGENTS.md).
