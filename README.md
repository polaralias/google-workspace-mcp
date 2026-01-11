# Google Workspace MCP Server

A comprehensive, highly performant Model Context Protocol (MCP) server for Google Workspace. This server provides LLMs with deep integration capabilities across the Google Workspace suite, including Gmail, Drive, Calendar, Docs, Sheets, Slides, Forms, Keep, Tasks, Admin SDK, People, and Meet.

## Features

-   **Broad Service Coverage**: Integrates with 12+ Google Workspace services.
-   **Tiered Tooling**: logical separation of tools into `core` (essential), `extended` (advanced), and `complete` (admin/sensitive) tiers.
-   **Dual Transport**: Supports both `stdio` (local) and `streamable-http` (SSE) transports.
-   **Flexible Auth**: Supports user OAuth (end-user flows) and Service Account + Domain-Wide Delegation (admin/server-to-server).
-   **Self-serve API Keys**: Optional auth service to issue user-bound API keys from `/`, with redirect support from connection URLs.
-   **Encrypted Local Config**: A deployment master key encrypts stored secrets in Postgres for local auth.
-   **Performance**: Built with `fastmcp` and `fastapi` for low latency and high concurrency.

## Supported Services

| Service | Description | Key Tools |
| :--- | :--- | :--- |
| **Gmail** | Email management | Search, Read, Send, Draft, Label management, Filter management |
| **Drive** | File storage | Search, Read content, Upload, Share, Lifecycle (copy/trash/delete), Revisions, Shared Drives |
| **Calendar** | Scheduling | List calendars, Manage events, Availability (Free/Busy), Meeting suggestions, ACLs |
| **Docs** | Document editing | Read content, Create/Update text, Styling, Export (PDF/Docx/HTML) |
| **Sheets** | Spreadsheets | Read/Write values, Formulae, Formatting, Pivot Tables, Charts, Data Validation |
| **Slides** | Presentations | Create slides, Add text/images, Styling, Export PDF |
| **Forms** | Surveys | Create forms, Batch update questions, Retrieve responses |
| **Keep** | Note taking | List/Get/Create notes, Manage attachments, Sharing (Note: Update/Patch not supported) |
| **Tasks** | Task management | List/Create/Update tasks, Due dates, Completion |
| **Chat** | Messaging | Send/Read messages, Manage spaces, Threaded replies |
| **People** | Contacts | List/Search contacts, Create/Update/Delete contacts, Directory search |
| **Meet** | Video conferencing | Access conference records, participants, recordings, transcripts |
| **Admin** | Administration | **Directory**: Manage Users, Groups, Members<br>**Reports**: Audit activities, Drive usage reports |
| **Search** | Custom Search | Programmable Search Engine integration |

## Quick Start

### Prerequisites

-   Python 3.10+
-   A Google Cloud Project with necessary APIs enabled.

### Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### Authentication

1.  **OAuth Client ID**: Create an OAuth 2.0 Client ID (Desktop app) in Google Cloud Console.
2.  **Download Credentials**: Save the JSON file as `credentials.json` in the root directory (or set `GOOGLE_CLIENT_SECRET_PATH`).
3.  **Run**:
    ```bash
    python main.py
    ```

For **Service Account** usage (Admin/Keep), set `GOOGLE_APPLICATION_CREDENTIALS` to your service account key file path. Ensure Domain-Wide Delegation is configured for the service account with appropriate scopes.

### User-bound API Keys (Local Auth Service)

Run the local auth service to store encrypted configuration and issue user-bound API keys:

-   **Required**: `MASTER_KEY` (64-hex string or passphrase) and `DATABASE_URL` (Postgres).
-   **Enable UI**: Set `API_KEY_MODE=user_bound` to expose `/`.
-   **Self-serve flow**: Visit `http://localhost:3000/` and complete the form. If you open a connection URL that includes `redirect_uri` (or `callback_url`) and optional `state`, the page will redirect back with `api_key` in the query string.

## Configuration

### Environment Variables

-   `PORT`: Server port (default: 8000)
-   `GOOGLE_OAUTH_CLIENT_ID`: OAuth Client ID
-   `GOOGLE_OAUTH_CLIENT_SECRET`: OAuth Client Secret
-   `USER_GOOGLE_EMAIL`: Default user email (optional)
-   `MCP_SINGLE_USER_MODE`: Enable single-user mode (true/false)

### Auth Service Environment Variables

-   `PORT`: Auth server port (default: 3000)
-   `MASTER_KEY`: Encryption key for local auth config (64-hex or passphrase)
-   `DATABASE_URL`: Postgres connection string for stored configs and API keys
-   `API_KEY_MODE`: Set to `user_bound` to enable `/`
-   `REDIRECT_URI_ALLOWLIST`: Comma-separated domains allowed to receive redirects
-   `CODE_TTL_SECONDS`: OAuth auth code TTL in seconds (default: 90)
-   `TOKEN_TTL_SECONDS`: Token TTL in seconds (default: 3600)

### Docker Compose (Local Auth + Database)

The `docker-compose.yml` includes a Postgres service and the auth server. Set `MASTER_KEY` in your `.env`, then run:

```bash
docker compose up
```

### Tool Tiers

Control which tools are exposed using the `--tool-tier` argument:

-   `core`: Basic read/write operations (safe for most users).
-   `extended`: Lifecycle management, complex operations, and bulk actions.
-   `complete`: Full administrative access, including destructive actions.

```bash
python main.py --tool-tier core
```

You can also filter specific services:

```bash
python main.py --tools gmail calendar --tool-tier core
```

## Important Notes

### Google Keep Integration
The Google Keep API REST surface does not currently include an `update` or `patch` method for note content. Therefore, the integration supports:
-   **Create** and **Retrieve** notes
-   **Delete** notes
-   **Download** attachments
-   **Manage** sharing permissions

It does **not** support editing existing note content, changing labels, colors, or pinning notes.

## API Enablement

To use the tools, enable the corresponding APIs in your Google Cloud Project:

-   [Google Calendar API](https://console.cloud.google.com/flows/enableapi?apiid=calendar-json.googleapis.com)
-   [Google Drive API](https://console.cloud.google.com/flows/enableapi?apiid=drive.googleapis.com)
-   [Gmail API](https://console.cloud.google.com/flows/enableapi?apiid=gmail.googleapis.com)
-   [Google Docs API](https://console.cloud.google.com/flows/enableapi?apiid=docs.googleapis.com)
-   [Google Sheets API](https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com)
-   [Google Slides API](https://console.cloud.google.com/flows/enableapi?apiid=slides.googleapis.com)
-   [Google Forms API](https://console.cloud.google.com/flows/enableapi?apiid=forms.googleapis.com)
-   [Google Tasks API](https://console.cloud.google.com/flows/enableapi?apiid=tasks.googleapis.com)
-   [Google Chat API](https://console.cloud.google.com/flows/enableapi?apiid=chat.googleapis.com)
-   [Google Keep API](https://console.cloud.google.com/flows/enableapi?apiid=keep.googleapis.com)
-   [People API](https://console.cloud.google.com/flows/enableapi?apiid=people.googleapis.com)
-   [Google Meet API](https://console.cloud.google.com/flows/enableapi?apiid=meet.googleapis.com)
-   [Admin SDK](https://console.cloud.google.com/flows/enableapi?apiid=admin.googleapis.com)

## License

MIT
