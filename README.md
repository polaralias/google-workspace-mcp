# google-workspace-mcp

Standalone Python/FastMCP server for Google Workspace with direct HTTP transport, static API-key auth, and no tunnel sidecar.

## Highlights

- Default MCP endpoint: `http://localhost:3002/mcp`
- Default health endpoint: `http://localhost:3002/health`
- Supports `GOOGLE_WORKSPACE_MCP_API_KEY`, `MCP_API_KEY`, or `MCP_API_KEYS`
- Preserves existing Google auth flows:
  - stored OAuth credentials in `.oauth/`
  - service-account credentials
  - Google Keep master-token access
  - `GOOGLE_API_KEY` for public-data-only requests

## Configuration

1. Copy `.env.example` to `.env`
2. Fill in the required values:
   - `GOOGLE_WORKSPACE_MCP_API_KEY`
   - one Google auth source:
     - persisted OAuth credentials in `.oauth/`
     - `GOOGLE_SERVICE_ACCOUNT_FILE` or `GOOGLE_SERVICE_ACCOUNT_JSON`
     - `GOOGLE_KEEP_MASTER_TOKEN`
     - `GOOGLE_API_KEY` for public-data-only tools

Common optional settings:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_IMPERSONATED_USER`
- `GOOGLE_DEFAULT_USER_EMAIL`
- `GOOGLE_KEEP_EMAIL`
- `GOOGLE_KEEP_MANAGED_LABEL`
- `GOOGLE_WORKSPACE_MCP_PORT`
- `GOOGLE_WORKSPACE_MCP_HOST_PORT`
- `GOOGLE_WORKSPACE_MCP_PATH`
- `API_KEY_MODE`

Docker Compose note:

- If a secret contains a literal `$`, escape it as `$$` in `.env`

Compatibility note:

- Legacy Keep managed labels using `google-workspace-fast-mcp` remain accepted for note edits

## Run Locally

```bash
python scripts/run_server.py serve
python scripts/run_server.py doctor
python scripts/run_server.py url
```

OAuth and Keep helper scripts remain available:

```bash
npm run google:oauth
npm run google:keep-master-token
```

The local helper automatically picks up repo-local `.oauth/` and `gws.json` when present.

## Run With Docker Compose

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

The included `docker-compose.yml` publishes the server on port `3002`, joins the external `reverse_proxy` network, and mounts `./.oauth` into the container so existing OAuth credentials continue to work without reauth.

If you use a service account file, add a bind mount such as:

```yaml
volumes:
  - ./.oauth:/app/.oauth
  - ./gws.json:/app/gws.json:ro
```

Then set `GOOGLE_SERVICE_ACCOUNT_FILE=/app/gws.json` in `.env`.

## Add To A Shared MCP Compose Project

Use this service in a larger compose stack when you want one project containing multiple MCP servers:

```yaml
services:
  google-workspace-mcp:
    build:
      context: /path/to/google-workspace-mcp
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - /path/to/google-workspace-mcp/.env
    environment:
      MCP_HOST: 0.0.0.0
      MCP_PORT: "3002"
      MCP_PATH: /mcp
      GOOGLE_MCP_CREDENTIALS_DIR: /app/.oauth
    volumes:
      - /path/to/google-workspace-mcp/.oauth:/app/.oauth
      # Optional if you use a service account file:
      # - /path/to/google-workspace-mcp/gws.json:/app/gws.json:ro
    ports:
      - "3002:3002"
    networks:
      - reverse_proxy

networks:
  reverse_proxy:
    external: true
```

If you do not need host port publishing because you are fronting the service with another internal proxy, you can omit the `ports` section.

## MCP Client Connection

- URL: `http://<host>:<port>/mcp`
- Header: `Authorization: Bearer <your-api-key>`

## Repository Notes

- Tool manifests are split by Google product area for easier control
- Health responses identify the server as `google-workspace-mcp`
- The Docker image is intended for direct HTTP deployment without any tunnel helper
