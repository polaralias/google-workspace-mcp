# google-workspace-mcp

Standalone Python/FastMCP server for Google Workspace and Google Keep master-token workflows.

The public server surface is intentionally limited to the 53 tools that have current support evidence. OAuth is the primary Google Workspace auth path. API key support is a narrow public-read compatibility path. Google Keep is supported only through the unofficial master-token flow.

## Endpoints

- MCP: `http://localhost:3002/mcp`
- Health: `http://localhost:3002/health`

## Primary Docs

- [Configuration reference](docs/configuration.md)
- [Verified support matrix](docs/product-specs/support-matrix.md)
- [Per-tool support matrix](docs/generated/tool-support-matrix.md)
- [Tool reference](docs/tool-reference.md)
- [Architecture](ARCHITECTURE.md)
- [Auth models](docs/product-specs/auth-models.md)
- [Plans and archive index](docs/PLANS.md)

## Supported Auth

- MCP bearer auth via `GOOGLE_WORKSPACE_MCP_API_KEY`, `MCP_API_KEY`, or `MCP_API_KEYS`
- Stored OAuth credentials in `.oauth/` or `GOOGLE_MCP_CREDENTIALS_DIR`
- `GOOGLE_API_KEY` for the documented public-read subset only
- `GOOGLE_KEEP_EMAIL` plus `GOOGLE_KEEP_MASTER_TOKEN` for Keep-only flows

## Local Run

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

## Docker Run

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

The bundled compose file is self-contained, publishes port `3002`, mounts `./.oauth` to preserve OAuth credentials, and starts without a repo-local `.env` file.

## Verification

Default contract suite:

```bash
uv run python -m unittest discover -s tests -v
```

Opt-in live Google validation:

```bash
$env:GOOGLE_WORKSPACE_MCP_RUN_LIVE_TESTS='true'
uv run python -m unittest discover -s tests -p "test_live_*_contract.py" -v
```

Opt-in Docker smoke validation:

```bash
$env:GOOGLE_WORKSPACE_MCP_RUN_DOCKER_TESTS='true'
uv run python -m unittest tests.test_docker_contract -v
```

## Publish Contract

- `uv run` is the supported local execution path.
- Manifest files define the public interface and now contain only the verified or verified-limited surface.
- Generated references are derived from manifests and support metadata; the family-level support matrix remains the canonical product contract.
