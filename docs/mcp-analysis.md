# **Analysis of MCP Repos: OAuth Support & Database Migration**

## 1. **OAuth 2.0 & Dynamic Client Registration Compliance**

All three MCP server implementations -- **ClickUp MCP**, **Google
Workspace MCP**, and **Personal Context MCP** -- adhere closely to the
Model Context Protocol's requirements for OAuth 2.0 authentication and
dynamic client registration. Each server supports a full **OAuth 2.0
Authorization Code flow with PKCE** (Proof Key for Code Exchange) and
implements **RFC 7591 Dynamic Client Registration (DCR)** for clients
like ChatGPT to register OAuth clients on the
fly[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11).
In practice, this means they expose the standard OAuth endpoints and
metadata:

-   **Well-Known OAuth Metadata:** Each server publishes an OAuth 2.0
    Authorization Server metadata document at the expected location
    (e.g. `/.well-known/oauth-authorization-server`). This JSON includes
    the authorization endpoint, token endpoint, and
    `registration_endpoint` needed for dynamic client
    registration[\[2\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts#L293-L301).
    For example, the ClickUp MCP advertises these endpoints
    (authorization at `/connect` or `/authorize`, token at `/token`, and
    client registration at `/register`) in its
    metadata[\[3\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts#L295-L303).
    The presence of a `registration_endpoint` signals to LLM clients
    (like ChatGPT) that they can perform DCR.

-   **Dynamic Client Registration Endpoint (**`POST /register`**):** All
    three servers provide an unauthenticated `POST /register` endpoint
    to accept OAuth client registrations as specified by RFC 7591. In
    each implementation, this endpoint validates the submitted
    `redirect_uris` and other client info, checks them against an
    allowlist of permissible domains, and generates a new `client_id`.
    For instance, the ClickUp MCP's code verifies that at least one
    redirect URI is provided and matches allowed domains before
    inserting a new client record in the
    database[\[4\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L58-L66)[\[5\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L82-L90).
    Similarly, the Google Workspace MCP performs these validations and
    inserts the client (prefixing IDs like `client_xxx` in its
    implementation)[\[6\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L352-L361)[\[7\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L370-L378).
    On success, the endpoints return a JSON containing the generated
    `client_id` (and optional fields like client name or auth
    method)[\[8\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L98-L106)[\[9\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L371-L378).
    The ClickUp MCP README even provides a PowerShell snippet to test
    DCR, confirming that posting to `/register` returns a new
    `client_id`[\[10\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L146-L154).
    This dynamic registration capability aligns with the MCP
    specification's mandate that servers **MUST** support RFC7591 for
    OAuth client
    setup[\[11\]](https://modelcontextprotocol.io/llms-full.txt#:~:text=the%20OAuth%202,MUST).

-   **OAuth Authorization Flow (Code Grant with PKCE):** Once a client
    is registered, the OAuth flow proceeds via the **Authorization Code
    grant**. The servers implement an `/authorize` **(or** `/connect`**)
    endpoint** where end-users are directed to grant access. In these
    MCP servers, the authorization step is coupled with collecting the
    user's configuration/API keys for the third-party service:

-   **GET /authorize** -- When invoked by a client (like ChatGPT) with
    query parameters including `client_id`, `redirect_uri`, `state`, and
    PKCE `code_challenge` + `method`, the server verifies the client and
    redirect URI. If valid and allowed, it shows the **"Connect" UI**
    for the user to input their credentials or config. A CSRF token is
    set as a cookie for
    security[\[12\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L424-L432)[\[13\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L432-L440).
    For example, Google Workspace MCP's `GET /authorize` will serve an
    HTML page (or redirect to the root connect page) after validating
    PKCE parameters and domain
    allowlist[\[14\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L384-L393)[\[12\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L424-L432).
    The ClickUp MCP behaves similarly, using a `/connect` page (which is
    functionally the same step under the hood).

-   **POST /authorize** -- When the user submits their configuration on
    the Connect UI, the server handles the form submission. It expects
    the CSRF token to match, and requires the provided config to include
    necessary fields (like an API key). The server then creates a
    **persistent "Connection" record** in its database, storing the
    user's config (with sensitive parts encrypted) and generating a
    one-time **authorization code**. It associates that code with the
    new connection and the requesting OAuth client. In ClickUp MCP, this
    logic lives in the auth router: after validating input, it calls
    `connectionManager.create()` to persist the config and then
    `authService.generateCode()` to create an auth code tied to that
    connection[\[15\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L199-L208)[\[16\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L206-L214).
    Google's implementation similarly inserts a new connection (with a
    foreign key to the client) and an auth code in one
    transaction[\[17\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L500-L508).
    The code is typically a short-lived random string (often hashed
    before storage) with an expiry (90 seconds by
    default[\[18\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L190-L198)).
    The server responds with a JSON containing a redirect URL back to
    the client's callback, appending `code=<auth_code>` and any state
    parameter[\[19\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L208-L216)[\[20\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L510-L518).
    (It returns a URL rather than a direct redirect to allow the
    front-end to handle navigation.)

-   **POST /token** -- Finally, the servers implement the **token
    exchange** endpoint where the client (e.g. ChatGPT) posts the auth
    code, its `code_verifier`, and client ID to get an access token. The
    server checks that the code is valid and not expired, verifies the
    PKCE code verifier against the saved challenge (ensuring the code
    was obtained by the legitimate client), and then issues a long-lived
    **access token**. In all three servers the access token is a
    **session identifier** (often a combination of a UUID and a secret,
    or a random string) that represents the user's authorized session.
    For example, the Google Workspace MCP checks the auth code's
    existence and validity (deletes it from the `auth_codes` table and
    retrieves the associated connection) and confirms the
    `code_verifier` matches the original challenge via
    SHA-256[\[21\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L544-L553)[\[22\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L570-L578).
    It then generates a new token (`mcp_at_...`) and stores a hashed
    version in the `sessions` table along with the connection ID and
    expiration
    timestamp[\[23\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L577-L585).
    The response includes `access_token` (the raw token string),
    `token_type: Bearer`, and `expires_in` (e.g. 3600 seconds by
    default)[\[24\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L220-L228)[\[25\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L580-L588).
    ClickUp MCP follows the same pattern (issuing tokens formatted as
    `session_id:session_secret`[\[26\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L122-L131)
    and storing a hash/server-side secret). All servers set the **token
    TTL** via configuration (one hour by
    default)[\[18\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L190-L198).

-   **OAuth2 Protected Resource & Identification:** The MCP spec also
    requires an OAuth-protected resource to advertise itself (RFC 8707 /
    RFC 9728). The servers fulfill this by providing a
    `.well-known/oauth-protected-resource` or similar metadata and by
    including `WWW-Authenticate` headers on unauthorized requests. For
    instance, the ClickUp MCP server, when a request to the MCP endpoint
    lacks valid auth, responds with a `401 Unauthorized` and a header
    pointing to its resource metadata:
    `WWW-Authenticate: Bearer realm="mcp", resource_metadata="<base-url>/.well-known/oauth-protected-resource"`[\[27\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/oauthDiscovery.ts#L11-L19).
    This directs clients (like ChatGPT) to discover how to initiate
    auth. The existence of these headers and well-known docs confirm
    alignment with the Model Context Protocol's OAuth requirements (MCP
    servers *"MUST implement OAuth 2.0 Protected Resource
    Metadata"*[\[11\]](https://modelcontextprotocol.io/llms-full.txt#:~:text=the%20OAuth%202,MUST)).

**Summary:** Across all three projects, the **OAuth implementation is
robust and in line with MCP docs**. They support OAuth 2.0 bearer tokens
and advertise `"authentication": ["api_key", "oauth2"]` in their
capability
metadata[\[28\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts#L281-L288).
They implement the **full authorization code flow with PKCE** to avoid
exposing user API keys to clients, and they include **Dynamic Client
Registration** to let ChatGPT (or other LLM-based clients) obtain a
`client_id` automatically. The presence of the DCR endpoints and proper
OAuth2 flows means issues like "missing dynamic registration" are
addressed -- e.g. the ClickUp MCP explicitly notes it **supports RFC
7591 DCR required by
ChatGPT**[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L137-L145)
and provides a registration endpoint in its OAuth meta. One caveat is
that **allowed redirect URIs must be configured**: each server uses a
redirect URI allowlist to guard DCR and auth flows. For example, by
default ClickUp MCP's compose file allows ChatGPT's domains and
localhost
callbacks[\[30\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L18-L26),
whereas Google Workspace MCP's sample `.env` requires setting
`REDIRECT_URI_ALLOWLIST` (e.g. to include
`chat.openai.com`)[\[31\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L56-L64).
If this is not done, registration or the authorization step will reject
unknown redirect URLs (as seen in Google's handler which returns *"URI
not in our allowlist"* errors unless the domain
matches[\[32\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L354-L362)[\[33\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L356-L364)).
Ensuring the allowlist includes the necessary client domains is
essential for the OAuth flow to complete successfully.

## 2. **Database Requirements in Container Deployments**

**Current State (PostgreSQL as Adjacent Service):** All three MCP
servers use a **persistent database (PostgreSQL)** to store
configuration and session data. When deploying via Docker or other
container systems, this means each server container is typically
accompanied by a Postgres container (or an external Postgres service)
that the app connects to. For example, the ClickUp MCP's recommended
setup uses **Docker Compose** to run the MCP server alongside a Postgres
15 instance -- "this package includes the MCP server and a PostgreSQL
database for persistent session
storage"[\[34\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L16-L24).
In the provided `docker-compose.yml`, we see a service named `db`
running the Postgres image, with the MCP server container depending on
it[\[35\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L38-L46).
Similarly, the Google Workspace MCP documentation lists PostgreSQL 14+
as a prerequisite and uses a Compose setup for easy
deployment[\[36\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L22-L30)[\[37\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L99-L108).
The Personal Context MCP also expects a `DATABASE_URL` pointing to a
Postgres
instance[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L27).
In all cases, the database is *required* -- the server will refuse to
start if no DB connection string is
provided[\[39\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L10-L18).

**Data Stored:** The PostgreSQL database is central to enabling
multi-user and secure sessions in these servers. Key information
persisted includes:

-   **OAuth Client registrations:** The dynamic client info from
    `/register` calls is saved in a `clients` table (client ID, name,
    allowed redirect URIs, etc.). For instance, the ClickUp schema
    defines a `clients` table with fields for `client_id` (PK),
    `client_name`, `redirect_uris` (stored as JSON array), and auth
    method[\[40\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L7).
    This allows the server to look up valid redirect URIs and client
    settings during the OAuth flows.

-   **User Connections / Configurations:** When a user "connects" their
    account (e.g. enters their ClickUp API key or Google credentials),
    the server creates a **Connection** record. This typically includes
    a generated UUID, a user-friendly name, and the user's config data
    (such as API keys or tokens) with sensitive parts encrypted. The
    schema has a `connections` table for
    this[\[41\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L9-L17).
    In ClickUp/Google, the connection holds the third-party API key
    (encrypted) and any metadata like team ID, permissions, etc., needed
    to serve requests on that user's behalf. These records are what the
    issued MCP API keys or OAuth tokens ultimately reference.

-   **OAuth Authorization Codes:** During the OAuth flow, the
    short-lived codes are stored in an `auth_codes` table. This table
    maps the one-time code (often hashed) to the connection and client,
    and notes its expiration. For example, the schema shows `auth_codes`
    with columns for the code (hashed), `connection_id` (foreign key to
    connections), `client_id` (foreign key to clients), `code_challenge`
    (for PKCE),
    etc[\[42\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L27-L35).
    This ensures the `/token` endpoint can validate incoming codes and
    apply the correct redirect URI and PKCE verification.

-   **Session Tokens:** Once exchanged, long-lived tokens (access
    tokens) are stored in a `sessions` table. Each session row holds a
    UUID id, the associated connection, a `token_hash` (the hashed token
    string for lookup -- the servers **never store raw bearer tokens**
    for security), creation and expiry timestamps, and a revoked
    flag[\[43\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L18-L26).
    This lets the server authenticate incoming requests: an incoming
    Bearer token is hashed and looked up in `sessions` to find the
    matching user config (and ensure it's not expired or revoked). We
    see an index on `token_hash` to speed up this
    lookup[\[44\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L44-L46).

-   **User-Bound API Keys:** In "user_bound" API key mode (an
    alternative auth method where a user can obtain an API key via the
    UI), the servers use additional tables like `user_configs` and
    `api_keys`. These store the encrypted config and a hashed API key
    string, respectively, tied to a user
    record[\[45\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L48-L57)[\[46\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L60-L69).
    This mechanism is similar in purpose to OAuth sessions, but uses API
    keys as Bearer tokens. The database tracks usage and can revoke keys
    individually.

-   **Caching and Other Data:** The servers also leverage the database
    for caching and misc. data to improve performance and maintain
    state. A notable example is the `cache` table present in ClickUp's
    schema[\[47\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46)
    -- this is used to store cached API responses or expensive lookups
    (e.g. project hierarchies, user data) with an expiry. By caching in
    the DB, the data persists across server restarts and can be shared
    across sessions. Indexes on the `expires_at` help in purging stale
    cache
    entries[\[48\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L42-L46).
    (Google Workspace MCP may cache things like Google Drive directory
    structures, and Personal Context MCP caches external info like bank
    holidays as seen in its schema.) Other tables in Personal Context
    MCP (e.g. `work_status_events`, `location_events`) record recent
    status signals -- also stored in Postgres for persistence.

**Environment & Networking:** To connect to these DBs, the applications
rely on a `DATABASE_URL` (or equivalent env vars for
host/user/password). For instance, Personal Context MCP requires
`DATABASE_URL` set to a Postgres connection string in the
environment[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L27),
and Google's `.env.example` shows
`DATABASE_URL=postgres://user:password@localhost:5432/gws_mcp`[\[49\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L52-L60).
In Docker Compose, this is often provided via an `.env` file and
environment interpolation. The ClickUp compose file sets
`DATABASE_URL=postgres://...@db:5432/clickup_mcp` pointing at the
companion `db` service on the Docker
network[\[50\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L20-L28)[\[51\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L22-L25).
The **Postgres container** is configured with matching
credentials/database (see the `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB` in the compose) and typically uses a volume
(`postgres_data`) to persist data on disk outside the container
lifecycle[\[35\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L38-L46)[\[52\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L44-L52).
This means the Postgres instance is "adjacent" -- running alongside the
MCP server and accessible over the Docker network.

**Operational Considerations:** Running an external DB introduces a few
requirements and points of potential failure:

-   The database must be **initialized and running** before the MCP
    server fully starts. The code attempts to run DB migrations on
    startup -- for example, ClickUp's server will retry applying its SQL
    schema up to 10 times with delays if the DB isn't
    ready[\[53\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L53-L62).
    If the DB container is slow to start, the MCP server logs "Database
    not ready,
    retrying\..."[\[54\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L63-L71).
    Only after the migrations succeed does the app proceed to accept
    connections[\[55\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L99-L107).
    If the DB never comes up or migrations fail, the server might
    ultimately crash on startup, or start in a semi-configured state. A
    misconfigured DB (wrong credentials, inaccessible host) will cause
    errors -- the code explicitly checks for `DATABASE_URL` on startup
    and throws if
    missing[\[39\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L10-L18),
    and any runtime query failures (e.g. lost connection) could result
    in unhandled exceptions or HTTP 500 errors for clients.

-   Indeed, one reported issue has been **HTTP 500 errors when
    finalizing configurations**, which often points to DB connection
    problems. For example, after a user submits the connect form (which
    triggers writing to the DB), a failure to insert the new connection
    or code (due to a DB outage or network issue) would throw an error
    -- the user would see a 500 and no token issued. The logs *"Failed
    to create connection"* or *"Failed to register client"* with a stack
    trace[\[56\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L376-L381)[\[57\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L516-L520)
    indicate the DB operation didn't succeed. These scenarios underscore
    that the **network link between the app container and the database**
    must be reliable. Docker networking issues or misalignment of
    container startups can lead to such failures. The composition uses
    `depends_on` to start Postgres
    first[\[58\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L32-L35),
    but that doesn't guarantee readiness, hence the retry logic.

-   **Performance & Scaling:** Postgres is a robust, multi-user
    database; it can handle concurrent queries from the MCP server
    (which uses a connection pool of up to 20 by
    default[\[59\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L18-L26))
    and can scale if the service grows. However, for a modest personal
    or small-team deployment, running a separate Postgres container can
    be heavyweight. It consumes additional memory/CPU and requires
    maintenance (e.g. updates, backups). In contrast, the actual data
    volumes here are relatively small (config records, tokens, and some
    caches). This opens the possibility of using a lighter-weight
    embedded database.

In summary, the current containerized setup **requires provisioning a
Postgres database alongside the app**. Proper configuration of
environment variables (as documented in each repo's README) is needed to
point the app to the DB. The database is used for critical security and
state data -- from OAuth tokens to encrypted API keys -- and is not just
an optional cache. Thus, any plan to simplify deployment by removing the
external DB must provide an alternative means to reliably store this
information.

## 3. **Migrating to a Local SQLite Database (Embedded DB)**

Moving from an external Postgres to an embedded **SQLite** (or similar
file-based DB) can simplify deployment and potentially resolve the DB
connectivity issues. The goal is to have the database **bundled within
the application container** -- eliminating cross-container network
dependencies -- while preserving all functionality (persistent storage,
caching, encryption, etc.) that Postgres provided. Below is an analysis
of the migration path and considerations:

**Feasibility and Tools:** All three MCP servers are written in
Node.js/TypeScript, which makes it feasible to switch to SQLite by using
a Node SQLite library or ORM: - Notably, the Personal Context MCP
already uses **Prisma ORM** for its database
layer[\[60\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L88-L96).
Prisma supports multiple database providers; by changing the datasource
from PostgreSQL to SQLite, the same data model can be used to generate a
SQLite database. Prisma would handle differences in types (e.g. it maps
JSON fields and arrays appropriately for SQLite). This suggests a
relatively straightforward path for Personal Context MCP -- the
developers can likely just update `schema.prisma` (switch
`provider = "postgresql"` to `"sqlite"` and adjust any unsupported
column types) and re-run migrations. The data model in Prisma already
abstracts JSON and DateTime types which SQLite can handle (JSON stored
as TEXT, DateTime as TEXT or REAL). - The ClickUp and Google Workspace
MCP servers currently use raw SQL queries via the `pg` module
(node-postgres). For these, the migration involves either adopting a
library (like `sqlite3` or `better-sqlite3` for direct queries, or a
lightweight ORM / query builder like **Knex**) or using an ORM like
Prisma similar to Personal Context MCP. Introducing Prisma to those
codebases would be a larger refactor (defining the schema and
refactoring queries to use Prisma client), but it would unify the
approach. Alternatively, one can implement a small abstraction: for
example, create a `db.ts` that uses `DATABASE_URL` to decide which
driver to use (pg vs. sqlite), and implement `query()` and transaction
helpers accordingly.

**Schema Adjustments:** The schema definitions in Postgres need to be
translated to SQLite DDL. Key adjustments include: - **Data Types:**
SQLite is schema-less in type enforcement but we should choose
appropriate affinities: - Postgres `TEXT` and `VARCHAR` -\> SQLite
`TEXT` (straight mapping). - `UUID` (used for IDs) -\> SQLite has no
native UUID type, but these can be stored as TEXT (36-char canonical
form or 32-char hex) or BLOB. Storing as TEXT is simplest. In Prisma's
schema for Personal Context, IDs are strings with `@default(uuid())`,
which works in SQLite by generating a GUID in text form. - `JSONB` -\>
SQLite does not have a native JSONB type. However, it does have a JSON
extension that treats JSON as text with some functions. We can store
JSON data as TEXT. For example, the `redirect_uris` array and `config`
object can be stored as JSON strings. In code, we then parse or generate
JSON when using these fields. The existing code already does JSON
serialization for Postgres: e.g. inserting a client in Postgres uses
`JSON.stringify()` on the `redirect_uris`
array[\[61\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L14-L20)
-- with SQLite we would do the same and store the result in a TEXT
column (and parse it on read if needed). - Arrays (Postgres `TEXT[]`)
-\> SQLite doesn't have array types; such fields (like Google MCP's
`grant_types_supported` list in metadata or the Personal Context's
`Client.grantTypes: String[]`) would likely be stored as JSON text as
well (e.g. `["authorization_code"]`). Prisma, for instance, maps a
string array to a JSON column on SQLite. - `TIMESTAMP`/`NOW()`: SQLite
can use `CURRENT_TIMESTAMP` as a default for a TEXT or NUMERIC column to
get the current time. Alternatively, the application can insert
timestamps manually. In the current code, many tables use
`DEFAULT NOW()` in Postgres and the code sometimes explicitly sets
timestamps. For example, in the ConnectionRepository update, they do
`updated_at = NOW()` in the
SQL[\[62\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ConnectionRepository.ts#L48-L56).
In SQLite, we could remove such raw SQL functions -- instead, set
`updated_at` in code (to `new Date()`) or use SQLite's `DATETIME('now')`
in the query. Since Node will be orchestrating transactions, it might be
simplest to handle timestamps in application logic. - **Auto-increment
keys:** Some tables in Personal Context (notably events) use serial
integers. SQLite's `INTEGER PRIMARY KEY` can auto-increment. This is
straightforward to map. - **Foreign Keys:** SQLite **supports foreign
key constraints** but requires enabling `PRAGMA foreign_keys = ON`. We
should ensure to turn that on at the start of the connection so that
relations (e.g. sessions -\> connections, auth_codes -\>
connections/clients) enforce referential integrity as in Postgres. All
the ON DELETE CASCADE rules can be defined in SQLite DDL similarly.
(Prisma's schema indicates `onDelete: Cascade` on relations which it
will implement in SQLite as
well[\[63\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L99-L107)[\[64\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L114-L117).) -
**Indexes:** Create indexes in SQLite for the same columns (e.g. on
`sessions.token_hash`, on `cache.expires_at`, etc.). The DDL syntax is
nearly identical (`CREATE INDEX IF NOT EXISTS idx_name ON table(column)`
works in SQLite as well).

In practice, we might maintain a separate `schema_sqlite.sql` or
dynamically adjust the existing `schema.sql` at runtime depending on DB
type. For example, remove the `JSONB` keyword or replace it with `TEXT`,
and omit unsupported parts. Given the schema is not huge (a handful of
tables), maintaining two versions is manageable. The migration script
can detect the `DATABASE_URL` scheme (`sqlite:` vs `postgres:`) and
choose the appropriate SQL.

**Code Changes -- Database Layer:** The database access code must be
adapted for SQLite: - **Connection & Query Interface:** The Postgres
code uses `Pool.query()` with parameterized SQL (`$1, $2`
placeholders)[\[65\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L12-L20).
SQLite libraries typically use `?` or named placeholders (`$foo`)
instead. We would need to adjust queries to SQLite's parameter style.
For example,
`pool.query("INSERT INTO clients (client_id, redirect_uris) VALUES ($1, $2)", [clientId, json])`
would become something like
`sqliteDb.run("INSERT INTO clients (client_id, redirect_uris) VALUES (?, ?)", [clientId, json])`.
If using an ORM (Prisma), explicit queries mostly go away in favor of
method calls (e.g. `prisma.client.create({...})`). - **Transactions:**
The code often groups operations in a transaction (for issuing keys, or
exchanging a token, to ensure atomicity). With Postgres they use either
explicit queries `BEGIN; ... COMMIT;` or a helper like `withTransaction`
that uses a client
connection[\[66\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L8-L16)[\[21\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L544-L553).
In SQLite, transactions are supported (through `BEGIN/COMMIT` or using
the library's transaction API). We'd implement a similar helper.
Notably, because SQLite by default has no concurrent writes, wrapping
multi-step operations in a transaction is actually beneficial to ensure
they lock the DB file once and complete quickly. We must be careful to
handle rollback on error just as in Postgres. - **Connection
Pooling/Concurrency:** In Postgres mode, the app can have many
concurrent queries handled by the pool (up to 20 client
connections)[\[59\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L18-L26).
With SQLite, it is often best to use a single connection (or a small
pool with serialized access) because a SQLite file cannot handle true
parallel writes. One strategy is to open the SQLite database in
serialized mode (if using `sqlite3` module, one can use `db.serialize()`
or open with `PARSE_DECLTYPES` etc. to ensure sequential execution of
queries). Another is to use a **file locking mode** like WAL
(Write-Ahead Logging) which allows concurrent reads and delayed writes.
In practice, given the expected load (a handful of users or agents
interacting), a single connection should suffice. The Node event loop
will queue the queries, and most operations (issuing a token,
registering a client) are very fast. We can remove the explicit pool
size of 20 -- or set it to 1 for SQLite. This reduces complexity and
avoids "database locked" errors that could happen if multiple
connections tried to write simultaneously. (SQLite will serialize a
single connection's queries automatically; multiple connections could
step on each other if not managed.) - **Query Logic Adjustments:** We
covered many under schema (like replacing `$1` with `?`, handling
`NOW()`). Another consideration is that some advanced SQL might differ.
However, these MCP servers use fairly simple queries (INSERT, SELECT,
DELETE by primary key, some joins for session lookup). SQLite can handle
all these. Even the join in Google's auth middleware
(`JOIN sessions s ON s.connection_id = c.id ... WHERE token_hash = ? AND expires_at > NOW()`)
can be done in SQLite (with `datetime('now')` for current time). The
logic for hashing and comparing tokens, etc., remains in application
code (they compute SHA-256 in Node, not in SQL, so no DB-specific crypto
functions needed).

**Maintaining Security Features:** A major concern is ensuring that
switching to SQLite does not weaken security or other functionality: -
**Encryption of sensitive data** -- This is done at the application
level using the `MASTER_KEY`. For example, when storing a user's API key
or OAuth refresh token, the code encrypts it with a symmetric key
derived from MASTER_KEY before saving to the `connections` or
`user_configs` table. This will remain unchanged. The same encrypted
blob that was stored in Postgres can be stored in SQLite. The MASTER_KEY
derivation and usage stays
identical[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L27).
Thus, secrets are safe in the SQLite file (an attacker would still need
the key to decrypt them). **Token hashing** also remains the same -- the
servers never store raw access tokens or API keys, only hashes, which
continues to protect against leakage. In short, **security is not
compromised by the DB change**, since encryption/hashing are implemented
in code, not reliant on the database. (It's wise to ensure file-level
security though -- e.g. the Docker container's filesystem or volume
should be protected and not world-accessible. But that is typically the
case with Docker volumes by default.) - **Caching & performance** -- The
caching layer (the `cache` table and similar) can be implemented in
SQLite equally. Since reads are frequent, we can enable SQLite's shared
cache mode or simply rely on OS file system caching. Given the data
volumes (likely small JSON blobs, maybe on the order of KBs each),
SQLite can handle hundreds or thousands of reads per second easily.
Writes (inserts/updates to cache) under moderate load are also fine,
though high write concurrency would be a limitation. If needed, one
could periodically prune expired cache entries to keep the file lean
(the Postgres schema has an index on `expires_at` for efficient cleanup
queries[\[47\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46),
similarly we can `DELETE ... WHERE expires_at < NOW()` in SQLite). -
**Integrity & Concurrency** -- One trade-off is that Postgres excels at
concurrent access and will maintain integrity under high load. SQLite
will serialize writes, which actually simplifies consistency (no two
writes ever conflict, they queue). The use-case here (agents calling the
MCP server) typically won't generate extreme write contention -- even
multiple parallel users each only write when connecting or refreshing a
token, which is infrequent. For reads (actual `/mcp` tool requests),
those occur via the SSE or HTTP endpoints and first pass through an auth
check. In Google's server, for example, each request does a `SELECT` on
sessions joined with connections to verify the
token[\[67\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L669-L672).
That's a simple primary-key lookup (on a hashed token) -- SQLite can
handle this quickly, especially with an index on token_hash. Even if
many read requests come in, SQLite allows concurrent reads (multiple
readers don't block each other in WAL mode). So performance for the
typical usage (which is likely I/O-bound on the external API calls more
than DB-bound) should not degrade noticeably. - **Disk space and
durability** -- The user indicated they will use a *bind mount with
plenty of disk space* for the SQLite DB. SQLite's file will grow as
records accumulate (but these applications don't create unbounded data;
mostly they store config and active sessions -- potentially the largest
could be audit logs or events if any, but those are bounded by retention
or can be vacuumed). With ample disk and periodic **VACUUM** (to reclaim
space from deleted rows, e.g. expired tokens), the SQLite file will
remain manageable. Durability is strong -- SQLite commits are
transactional and fsync by default, so data should be safe on disk.
Backups are as simple as copying the file (versus needing a pg_dump
process for Postgres).

**Migration Process:** Converting an existing deployment from Postgres
to SQLite would involve a few steps: 1. **Implement Code Support:**
Incorporate the SQLite driver/ORM changes described. This includes
writing migration logic for SQLite (perhaps converting the existing
schema or using an ORM migration). 2. **Testing:** Thoroughly test the
OAuth flow and API key issuance with the new DB to catch any SQL
differences. Ensure that client registration, the connect flow, token
issuance, and authenticated `/mcp` requests all work. Also test the
fallback API key auth if in use, and that cache entries can be written
and read. 3. **Data Migration (if needed):** If there is existing user
data in Postgres that needs to be preserved, one would export it. For a
small-scale deployment, this could be done by writing a script that
reads all rows from each relevant table via PG and inserts them into the
SQLite DB (ensuring IDs and hashes remain the same). Since the schemas
are similar, this is straightforward. If downtime can be afforded, an
alternative is to ask users to re-create their connections (especially
if there are not many) -- i.e. start fresh with an empty SQLite. The
dynamic nature of the system means users can always reconnect their
accounts to generate new tokens. However, keeping the same `client_id`s
for any already-registered OAuth clients (like ChatGPT) might be
important -- we could carry over the `clients` table data to avoid
requiring re-registration on the ChatGPT side.

**Benefits Expected:** Once the migration is done, each MCP server will
run as a single container including its own lightweight database: - **No
external DB dependency:** This removes the class of errors where the app
can't reach the DB or loses connection (which were causing those HTTP
500s). There is no network hop; database calls are in-process file I/O.
For example, finalizing a user's config will simply write to the local
DB file -- if the file is available (mounted) and not locked by another
process, it should always succeed absent disk issues. This should
resolve the "failed DB connection" errors encountered during OAuth
flows. - **Simpler deployment & maintenance:** One doesn't need to
manage a Postgres service (no need to set a POSTGRES_PASSWORD, open a
5432 port, etc.). The configuration boils down to providing a path for
the SQLite file (which could even default to something like
`/data/mcp.sqlite` inside the container). Backups can be taken by
copying that file. Upgrades are easier since the schema migrations can
run on SQLite at startup just as they did for PG. - **Resource usage:**
For a small server, SQLite's footprint is minimal -- it will use memory
only for cache pages and the library itself, instead of running a
separate database server process. This can be important if these MCP
servers are running on limited hardware or edge environments.

**Potential Caveats:** It's worth noting a few caveats post-migration: -
If in the future a need arises to **scale out** (multiple instances of
the MCP server behind a load balancer for higher traffic), a file-based
DB would become a bottleneck (multiple containers can't easily share a
single SQLite file). In that scenario, one might revert to a networked
DB or consider a different approach (like each instance having its own
DB and a syncing mechanism). But for the intended use (personal or
small-team contexts), a single instance is usually sufficient. - Some
advanced Postgres features won't be available. For example, if the code
ever relied on PG-specific JSON queries or full-text search, those would
not directly work in SQLite. Currently, the code does not use such
features -- it treats JSON mostly as opaque (storing and retrieving
whole config objects) and does filtering in application code (e.g.,
checking if a redirect URI is in the allowed list in memory). So this is
not an issue now. - **Testing and edge cases:** One should test things
like: what happens if two requests try to exchange tokens at the exact
same time (to verify the transaction logic in SQLite doesn't deadlock --
likely fine), or if the server is shut down in the middle of writing
(SQLite should rollback incomplete transactions on next open). Ensuring
the SQLite DB is opened with appropriate flags (journaling mode = WAL
perhaps) will help with robustness.

Overall, migrating to SQLite is **practical and expected to maintain
full functionality**. The MCP servers will still cache data and enforce
security exactly as before -- for example, **encrypted secrets remain
encrypted** (the Master Key mechanism is unchanged) and **session tokens
remain hashed** in the database. The main difference is these records
live in a `.db` file on disk instead of an external Postgres instance.
This change addresses the original pain points (OAuth flow failures due
to DB connectivity), providing a more self-contained deployment without
sacrificing the features that Postgres offered (persistent storage, data
integrity, and queryable structured
data)[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11)[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L27).
The result should be a more robust MCP server deployment that is easier
to set up and less error-prone in containerized environments.

**Sources:**

-   MCP Servers OAuth2/DCR Support -- *Personal Context MCP
    README*[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11)[\[60\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L88-L96);
    *ClickUp MCP README (ChatGPT/OAuth
    section)*[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L137-L145)[\[10\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L146-L154);
    *Auth router code
    excerpts*[\[4\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L58-L66)[\[24\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L220-L228);
    *Google Workspace server
    code*[\[6\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L352-L361)[\[23\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L577-L585);
    *MCP spec
    reference*[\[11\]](https://modelcontextprotocol.io/llms-full.txt#:~:text=the%20OAuth%202,MUST)
-   Postgres DB usage & schema -- *ClickUp MCP README
    (Docker)*[\[34\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L16-L24);
    *Personal Context MCP
    config*[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L27);
    *Docker Compose
    file*[\[35\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L38-L46);
    *Schema
    definitions*[\[42\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L27-L35)[\[47\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46);
    *Client repository (JSON
    usage)*[\[61\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L14-L20);
    *Connection repo (timestamp
    usage)*[\[62\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ConnectionRepository.ts#L48-L56);
    *DB pool
    config*[\[59\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L18-L26).

------------------------------------------------------------------------

[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11)
[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L27)
[\[60\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L88-L96)
README.md

<https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md>

[\[2\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts#L293-L301)
[\[3\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts#L295-L303)
[\[28\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts#L281-L288)
worker.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/worker.ts>

[\[4\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L58-L66)
[\[5\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L82-L90)
[\[8\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L98-L106)
[\[15\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L199-L208)
[\[16\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L206-L214)
[\[19\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L208-L216)
[\[24\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L220-L228)
authRouter.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts>

[\[6\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L352-L361)
[\[7\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L370-L378)
[\[9\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L371-L378)
[\[12\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L424-L432)
[\[13\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L432-L440)
[\[14\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L384-L393)
[\[17\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L500-L508)
[\[20\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L510-L518)
[\[21\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L544-L553)
[\[22\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L570-L578)
[\[23\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L577-L585)
[\[25\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L580-L588)
[\[32\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L354-L362)
[\[33\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L356-L364)
[\[56\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L376-L381)
[\[57\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L516-L520)
[\[66\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L8-L16)
[\[67\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L669-L672)
server.ts

<https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts>

[\[10\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L146-L154)
[\[18\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L190-L198)
[\[26\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L122-L131)
[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L137-L145)
[\[34\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L16-L24)
README.md

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md>

[\[11\]](https://modelcontextprotocol.io/llms-full.txt#:~:text=the%20OAuth%202,MUST)
Get Time App

<https://modelcontextprotocol.io/llms-full.txt>

[\[27\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/oauthDiscovery.ts#L11-L19)
oauthDiscovery.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/oauthDiscovery.ts>

[\[30\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L18-L26)
[\[35\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L38-L46)
[\[50\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L20-L28)
[\[51\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L22-L25)
[\[52\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L44-L52)
[\[58\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml#L32-L35)
docker-compose.yml

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docker-compose.yml>

[\[31\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L56-L64)
[\[36\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L22-L30)
[\[37\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L99-L108)
[\[49\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L52-L60)
README.md

<https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md>

[\[39\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L10-L18)
[\[59\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L18-L26)
index.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts>

[\[40\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L7)
[\[41\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L9-L17)
[\[42\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L27-L35)
[\[43\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L18-L26)
[\[44\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L44-L46)
[\[45\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L48-L57)
[\[46\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L60-L69)
[\[47\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46)
[\[48\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L42-L46)
schema.sql

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql>

[\[53\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L53-L62)
[\[54\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L63-L71)
[\[55\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L99-L107)
index.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts>

[\[61\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L14-L20)
[\[65\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L12-L20)
ClientRepository.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts>

[\[62\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ConnectionRepository.ts#L48-L56)
ConnectionRepository.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ConnectionRepository.ts>

[\[63\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L99-L107)
[\[64\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L114-L117)
schema.prisma

<https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma>
