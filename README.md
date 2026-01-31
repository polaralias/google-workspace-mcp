# Google Workspace MCP Server

A comprehensive Model Context Protocol (MCP) server for Google Workspace, built with **TypeScript** and **Node.js**.  This server provides seamless integration with the Google Workspace suite for AI assistants and automation tools.

## Supported Services

| Service | Description | Key Tools |
| : --- | :--- | : --- |
| **Gmail** | Email management | Search, Read content, List messages |
| **Calendar** | Scheduling | List calendars, Get events, Create/Delete events |
| **Drive** | File storage | Search, List files, Read content, Create files, Permissions |
| **Docs** | Document editing | Create doc, Get content, Modify text |
| **Sheets** | Spreadsheets | List spreadsheets, Get info, Read/Write values |
| **Slides** | Presentations | Create presentation, Get details, Create slides, Add textboxes |
| **Chat** | Messaging | List spaces, members, messages; Send messages |
| **Tasks** | Task management | List task lists, tasks; Create/Update/Delete tasks |
| **Admin** | Administration | **Directory**:  Manage Users, Groups; **Reports**:  Audit activities |

## Quick Start

### Prerequisites

- Node.js 20+
- SQLite (no external DB required)
- A Google Cloud Project with necessary APIs enabled

### Installation

```bash
# Clone the repository
git clone https://github.com/polaralias/google-workspace-mcp.git
cd google-workspace-mcp

# Install dependencies
npm install

# Build the project
npm run build
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:

```env
# Required
PORT=3000
DATABASE_URL=sqlite:///data/mcp.db
MASTER_KEY=your-64-character-hex-key-for-encryption

# Google OAuth (required for OAuth flow)
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Optional
API_KEY_MODE=user_bound
REDIRECT_URI_ALLOWLIST=localhost,127.0.0.1
BASE_URL=https://your-public-domain.example
TRUST_PROXY=1
```

### Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Google Slides API
   - Google Chat API
   - Google Tasks API
   - Admin SDK (for Admin tools)

4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Add `http://localhost:3000/auth/google/callback` to Authorized Redirect URIs

### Running the Server

```bash
# Development mode (with hot reload)
npm run dev

# Production mode
npm run build
npm start
```

The server will start on `http://localhost:3000` (or your configured PORT).

### Docker Deployment

```bash
# Set required environment variables
export MASTER_KEY=your-64-char-hex-key

# Start with docker-compose
docker-compose up -d
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with dependency status |
| `/api/health/live` | GET | Liveness probe |
| `/api/health/ready` | GET | Readiness probe |
| `/. well-known/mcp-configuration` | GET | MCP discovery configuration |
| `/auth/google` | GET | Start Google OAuth flow |
| `/auth/google/callback` | GET | OAuth callback handler |
| `/connect` | GET/POST | MCP client connection flow |
| `/token` | POST | Token exchange endpoint |
| `/register` | POST | Register new OAuth client |
| `/sse` | GET | Server-Sent Events for MCP |
| `/messages` | POST | MCP message handler |

## CLI Usage

```bash
# List all connections
npm run cli -- connections list

# Delete a connection
npm run cli -- connections delete <connection-id>

# List API keys
npm run cli -- api-keys list

# Revoke an API key
npm run cli -- api-keys revoke <api-key-id>
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `3000` | Server port |
| `DATABASE_URL` | Yes | - | SQLite connection string (e.g. `sqlite:///data/mcp.db`) |
| `MASTER_KEY` | Yes | - | Encryption key (64 hex chars recommended) |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes* | - | Google OAuth Client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes* | - | Google OAuth Client Secret |
| `API_KEY_MODE` | No | - | Set to `user_bound` to enable API key mode |
| `REDIRECT_URI_ALLOWLIST` | No | - | Comma-separated list of allowed redirect domains |
| `WORKSPACE_EXTERNAL_URL` | No | - | Public base URL used for OAuth metadata and redirects |
| `BASE_URL` | No | - | Alias of `WORKSPACE_EXTERNAL_URL` (public base URL) |
| `TRUST_PROXY` | No | - | Express trust proxy setting (e.g. `1`, `true`, `false`) |
| `GOOGLE_MCP_CREDENTIALS_DIR` | No | `~/.google_workspace_mcp/credentials` | Credential storage path |
| `CODE_TTL_SECONDS` | No | `90` | Auth code expiry time |
| `TOKEN_TTL_SECONDS` | No | `3600` | Access token expiry time |
| `LOG_LEVEL` | No | `info` | Logging level (debug, info, warn, error) |

*Required for OAuth authentication flow

## Development

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Type check
npm run build

# Run in development mode
npm run dev
```

## Security Considerations

- Always use a strong, random `MASTER_KEY` in production (64 hex characters)
- Never commit `.env` files to version control
- Use HTTPS in production
- Review and restrict OAuth scopes as needed
- Rotate credentials periodically

## License

MIT
