# Google Workspace MCP Server

A comprehensive Model Context Protocol (MCP) server for Google Workspace, now built with **TypeScript** and **Node.js**. This server provides seamless integration with the Google Workspace suite for LLMs.

## Supported Services

| Service | Description | Key Tools |
| :--- | :--- | :--- |
| **Gmail** | Email management | Search, Read content, List messages |
| **Calendar** | Scheduling | List calendars, Get events, Create/Delete events |
| **Drive** | File storage | Search, List files, Read content, Create files, Permissions |
| **Docs** | Document editing | Create doc, Get content, Modify text |
| **Sheets** | Spreadsheets | List spreadsheets, Get info, Read/Write values |
| **Slides** | Presentations | Create presentation, Get details, Create slides, Add textboxes |
| **Chat** | Messaging | List spaces, members, messages; Send messages |
| **Tasks** | Task management | List task lists, tasks; Create/Update/Delete tasks |
| **Admin** | Administration | **Directory**: Manage Users, Groups; **Reports**: Audit activities |

## Quick Start

### Prerequisites

-   Node.js 20+
-   A Google Cloud Project with necessary APIs enabled.

### Installation

```bash
# Install dependencies
npm install

# Build the project
npm run build
```

### Configuration

Create a `.env` file in the root directory:

```env
PORT=8000
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
# Other optional variables...
```

### Authentication

1.  **OAuth Client ID**: Create an OAuth 2.0 Client ID (Web application) in Google Cloud Console.
2.  **Redirect URI**: Add `http://localhost:8000/oauth/callback` (or your deployment URL) to Authorized Redirect URIs.
3.  **Start Server**: `npm start`
4.  **Connect**: Open `http://localhost:8000/connect` (if implemented) or use the authentication flow provided by your MCP client.

### CLI

The project includes a CLI for managing credentials and server operations:

```bash
npm run cli -- help
```

## Tool Tiers & Enablement

Enable the following APIs in your Google Cloud Project:
-   Gmail API
-   Google Calendar API
-   Google Drive API
-   Google Docs API
-   Google Sheets API
-   Google Slides API
-   Google Chat API
-   Google Tasks API
-   Admin SDK (for Admin tools)

## Development

```bash
# Run in development mode with reload
npm run dev

# Run build
npm run build
```

## License

MIT
