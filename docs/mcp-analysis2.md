# Analysis of MCP Servers: OAuth Alignment and Database Strategy

## OAuth 2.0 and Dynamic Client Registration Support

All three Model Context Protocol (MCP) servers (ClickUp MCP, Google
Workspace MCP, and Personal Context MCP) implement full OAuth 2.0
authorization flows with PKCE and support **Dynamic Client Registration
(RFC 7591)** for OAuth clients (e.g.
ChatGPT)[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11)[\[2\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L135-L143).
Each server provides the standard OAuth endpoints:

-   **Client Registration (**`POST /register`**)** -- Allows OAuth
    clients to dynamically obtain a `client_id` by providing redirect
    URIs[\[3\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L58-L67)[\[4\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L95-L103).
    For example, the ClickUp MCP's `/register` endpoint validates the
    provided `redirect_uris` against an allowlist and then inserts a new
    client record in the
    database[\[5\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L74-L83)[\[4\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L95-L103),
    returning a generated
    `client_id`[\[6\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L98-L106).
    Google Workspace MCP and Personal Context MCP have similar
    implementations (with Google MCP limiting registration to allowed
    domains and Personal Context MCP using Prisma to create a new
    `Client`
    row)[\[7\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L370-L378)[\[8\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L60-L68).

-   **Authorization Endpoint (**`GET/POST /authorize`**)** -- Supports
    the OAuth **Authorization Code** flow with PKCE. Users are
    redirected to a configuration UI (`/connect` or `/authorize`) to
    input their API credentials and approve access. The server then
    creates a persistent **Connection** (stores config and encrypted
    secrets) and generates a one-time auth code tied to that
    connection[\[9\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L207-L215).
    For example, in ClickUp MCP the POST `/authorize` handler verifies
    the CSRF token, ensures the provided `client_id` and `redirect_uri`
    are valid, then creates a new connection record and issues an auth
    code associated with that
    connection[\[10\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L199-L208)[\[11\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L210-L218).
    The user is finally redirected back to the client's callback URL
    with the `code` parameter.

-   **Token Endpoint (**`POST /token`**)** -- Handles exchanging the
    auth code for an **access token** (session token). All servers
    implement this to validate the code, verify PKCE, and issue a
    long-lived session token. For example, Google Workspace MCP's
    `/token` endpoint checks the code against the `auth_codes` table
    (ensuring it's unused and not expired), verifies the code's
    `client_id` and `redirect_uri` match, and validates the PKCE
    `code_verifier`[\[12\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L545-L554)[\[13\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L571-L580).
    It then inserts a new `session` record in the database and returns a
    Bearer `access_token` (with TTL) to the
    client[\[14\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L577-L586)[\[15\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L588-L595).
    ClickUp MCP and Personal Context MCP follow the same pattern
    (deleting or marking the auth code as used, creating a `Session`
    record, and returning a
    token)[\[16\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L220-L229)[\[17\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L582-L590).

-   **OAuth2 Discovery Endpoints** -- Each server exposes the standard
    `.well-known` endpoints so that OAuth clients (like ChatGPT) can
    discover the OAuth configuration. For example,
    `GET /.well-known/oauth-authorization-server` returns metadata
    including the authorization, token, and registration
    endpoints[\[18\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L248-L256).
    ClickUp MCP's implementation returns the `issuer`,
    `authorization_endpoint`, `token_endpoint`, and
    `registration_endpoint` (with supported grant and PKCE
    methods)[\[19\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L248-L257).
    Personal Context MCP similarly serves
    `.well-known/oauth-authorization-server` under its `/oauth` path,
    and also provides `/.well-known/oauth-protected-resource` metadata
    as per RFC
    9728[\[20\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L224-L232)[\[21\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L250-L258).
    (Google's MCP provides the authorization server metadata and a basic
    MCP config
    endpoint[\[22\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L109-L116)[\[23\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L129-L133),
    though it may not explicitly return the `authorization_servers` list
    as the others do.) These discovery endpoints ensure **ChatGPT
    compatibility**, as noted in the ClickUp MCP README ("supports RFC
    7591 Dynamic Client Registration (DCR) required by ChatGPT for OAuth
    integration"[\[2\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L135-L143)).

Overall, the codebases align well with the **Model Context Protocol's
OAuth requirements**. They implement **OAuth 2.1 style flows** (auth
code + PKCE), issue and store session tokens securely, and provide
**dynamic client registration** for seamless client onboarding. Notably,
the Personal Context MCP README explicitly highlights OAuth 2.0 and
RFC 7591 support as key
features[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11).
This indicates the design of all three servers is in line with MCP
specifications for OAuth: they act as OAuth2 Authorization Servers
protecting the MCP resource, enabling third-party AI agents to obtain
tokens on users' behalf.

## Database Dependencies in Container Deployments

Each MCP server uses a **PostgreSQL database** for persistence of
configurations and sessions, which in Docker deployments runs as an
adjacent container. In local Docker Compose setups, the MCP service
depends on a Postgres service for storing client registrations,
connection profiles, auth codes, session tokens, API keys, and cached
data. For example, the Google Workspace MCP's Docker Compose file
defines a `db` service running `postgres:16-alpine`, with the app
container's `DATABASE_URL` pointing to that Postgres instance (on the
Docker
network)[\[24\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L10-L18)[\[25\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L36-L44).
The app's environment requires setting `DATABASE_URL` to a Postgres
connection string (as well as a `MASTER_KEY` for encryption) before
startup[\[26\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L52-L60).
Similarly, the Personal Context MCP lists `DATABASE_URL` as a required
env var and expects a Postgres connection (the example `.env` uses
`postgres://user:pass@host:5432/db`)[\[27\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L26).

**Schema & Data:** All three servers create essentially the same schema
in Postgres (with minor variations for their domain). Tables include
`clients` (OAuth clients), `connections` (user connection configs),
`auth_codes`, `sessions`, `user_configs` & `api_keys` (for the
user-bound API key mode), and a `cache` table for hierarchy or config
caching[\[28\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L10)[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46).
For instance, ClickUp MCP's schema uses JSONB columns for storing lists
of redirect URIs and config blobs, and UUID primary keys for connections
and
sessions[\[30\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L9)[\[31\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L18-L26).
The **Postgres DB is thus critical** for the OAuth flow -- e.g. when a
user initiates a connection, the server inserts records into
`connections` and `auth_codes`; when the client exchanges a code, the
server queries and deletes that `auth_codes` row and creates a
`sessions`
entry[\[12\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L545-L554)[\[17\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L582-L590).
If the database is unreachable or not initialized, these steps fail
(leading to HTTP 500 errors during the `/authorize` or `/token` steps,
as has been observed).

**Deployment Considerations:** In container deployments, one must ensure
the database is available and **migrations have run** before the MCP
server handles requests. The code tries to mitigate startup issues --
for example, ClickUp MCP retries applying migrations up to 10 times if
the DB isn't
ready[\[32\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L58-L67)[\[33\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L72-L80).
Still, misconfigurations or networking issues (e.g. wrong DB host,
container linkage problems) can cause runtime failures (e.g. failing to
save a new session, yielding a 500 error when finalizing OAuth). Each
service's documentation stresses setting the DB password and connection
properly (ClickUp's quick start notes that the Docker image excludes
`.env` files, so you must pass the env vars for DB credentials to avoid
"role does not exist"
errors[\[34\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L10-L18)).
In practice, running multiple MCP servers means running multiple
Postgres instances or a shared instance with separate databases,
increasing complexity. Each server by default uses a distinct DB
name/user (for example, Google MCP defaults to `gws_mcp` DB and user in
its compose
file[\[35\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L40-L48),
while ClickUp MCP likely uses its own). They listen on different ports
(3011 for ClickUp, 3000 for others) and thus their DB containers can map
to different host ports to avoid conflict (Google's example maps
Postgres to port 5433 on the
host[\[36\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L42-L45)).

In summary, **the requirement is that a PostgreSQL service runs
alongside each MCP server**. The servers are tightly coupled to Postgres
via the `DATABASE_URL`. Without a running Postgres (or if credentials
are wrong), the MCP server will not complete initialization or will
error on any auth flow step that hits the database (e.g. issuing
tokens). This external DB dependency in Docker means extra configuration
(networking, volume for data) and has been a source of deployment
issues. The desire to simplify this leads to the proposed migration to
an embedded database like SQLite.

## Migration Path: Moving to an Embedded SQLite Database

Transitioning the MCP servers from Postgres to a **local SQLite
database** can eliminate the networking and container orchestration
issues by keeping persistence within the application container. The main
considerations for such a migration are compatibility and preserving the
current security/cache functionality:

-   **Schema Compatibility:** Most of the schema can be carried over to
    SQLite with minor tweaks. SQLite does not support the `JSONB` type
    or UUID type natively, but these can be mapped to standard types:

-   Use `TEXT` (or SQLite's `JSON` affinity) for JSON fields. For
    example, the ClickUp MCP `clients.redirect_uris` and
    `connections.config` columns (defined as JSONB in Postgres) could be
    stored as text containing JSON in
    SQLite[\[30\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L9)[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46).
    The application already serializes/deserializes JSON when storing
    and retrieving (e.g. `JSON.stringify(redirectUris)` before
    insert[\[37\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L14-L19),
    and parsing on fetch), so this change is mostly transparent in code.
    SQLite's JSON extension (available in modern versions) can even
    index/query JSON if needed, though that's likely unnecessary for
    simple usage.

-   UUID primary keys can be stored as TEXT (36-character strings). The
    code already generates UUIDs in application logic (using libraries
    or `crypto.randomUUID()`), so instead of relying on a Postgres UUID
    type/default, the app can supply the IDs. For instance, Personal
    Context MCP's Prisma schema uses `@default(uuid())` for IDs in
    Postgres[\[8\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L60-L68)[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L76-L84);
    in SQLite, Prisma will treat UUID defaults differently, but we can
    generate IDs in code or use a function for it. Alternatively, use
    SQLite's `INTEGER PRIMARY KEY` for some tables if auto-increment
    fits (though for consistency, keeping them as strings is fine).

-   Replace any Postgres-specific SQL. For example, `NOW()` in Postgres
    becomes `CURRENT_TIMESTAMP` in SQLite for default timestamps. The
    schema and migration scripts should be adjusted accordingly. Also,
    **UPSERT syntax** differs: Postgres uses `ON CONFLICT DO UPDATE`,
    whereas SQLite supports a similar `ON CONFLICT ... DO UPDATE` (since
    v3.24) or the simpler `INSERT OR REPLACE`. The code will need slight
    changes for queries like the cache insert (which in Postgres does
    `ON CONFLICT (key) DO UPDATE`[\[39\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/CacheRepository.ts#L14-L22)).
    In SQLite, this could be `INSERT OR REPLACE INTO cache ...` or using
    the newer upsert syntax. These query adjustments are relatively
    small.

-   **Code Changes:** Each server would need to use a SQLite driver or
    ORM instead of the Node Postgres client (`pg` module) it uses now.
    For ClickUp and Google Workspace MCP (which currently use raw SQL
    queries via `pg`), this implies swapping out the database layer:

-   One approach is to use an **ORM like Prisma or Knex** that supports
    both Postgres and SQLite. For example, Personal Context MCP already
    uses Prisma (which can target SQLite). Migrating it is as simple as
    changing the `datasource` provider to `"sqlite"` and updating the
    `DATABASE_URL` to a file path (e.g. `file:./mcp.db`), then running
    `prisma migrate` to create the SQLite schema. The existing Prisma
    models (for Clients, Connections, AuthCode, Session, etc.) can
    largely remain the same --- Prisma will handle differences (it maps
    JSON fields to TEXT in SQLite, and uses its own strategy for UUID
    defaults). This means Personal Context MCP can be moved to SQLite
    with minimal code changes, leveraging Prisma's cross-db
    compatibility.

-   For ClickUp and Google MCP, which currently hand-write SQL, adopting
    an ORM might be a bigger refactor. A lighter alternative is to use a
    **SQLite client library** (like `better-sqlite3` or `sqlite3` for
    Node) and adjust the repository functions. The query logic in those
    servers is straightforward (CRUD operations for the tables), so it's
    feasible to replace `pg.pool.query(...)` calls with SQLite prepared
    statements. For example, the `ClientRepository.create()` in ClickUp
    inserts a row into
    `clients`[\[40\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L11-L19);
    in SQLite, after establishing a connection to the `.db` file, an
    equivalent `db.prepare("INSERT INTO clients ...").run(...)` could be
    used. Similarly, selection queries
    (`SELECT * FROM clients WHERE client_id = ?`) will work with SQLite
    (with JSON text coming back instead of JSONB). The main effort is
    ensuring all queries are ported and any differing syntax is handled.

-   **Migration of Data:** If these servers are already in production
    with data in Postgres, a one-time migration of that data into SQLite
    would be needed (exporting to SQL or CSV and importing). If not, or
    if a fresh start is acceptable, the application can initialize a new
    SQLite database. The servers have migration scripts for setting up
    tables (e.g. ClickUp MCP's startup runs `runMigrations()` which
    executes the schema SQL on the configured
    DB[\[41\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L100-L108)).
    We can create a SQLite-compatible schema script from the existing
    one (e.g. convert types in `schema.sql` accordingly) and have the
    app execute that at startup for SQLite.

-   **Caching and Security Implications:** Using SQLite should
    **preserve all functional behavior** regarding caching and
    encryption. The caching layer in each server simply reads/writes
    JSON values in the `cache` table -- this will work the same in
    SQLite (though we lose Postgres's JSONB indexing, it's not critical
    for the modest cache table). Security-wise, secrets (API keys,
    tokens) are encrypted at the application level using the
    `MASTER_KEY` before being stored, so the encryption does not depend
    on the database
    engine[\[42\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docs/design/local_deployment.md#L98-L105).
    SQLite will store the already-encrypted blobs just as securely as
    Postgres (file system permissions for the `.db` file should be kept
    strict, but in a container with a bind mount this is manageable).
    The **session tokens** are stored as hashed values (SHA-256 or
    similar) in the sessions
    table[\[43\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L576-L585),
    which again does not rely on any Postgres-specific feature. In
    short, SQLite can meet the same confidentiality and integrity
    requirements as Postgres for this use case.

-   **Performance and Concurrency:** SQLite uses file-based storage and
    allows multiple readers but single-writer locking. Given the
    expected usage (a relatively low volume of writes -- only when new
    connections or tokens are issued -- and occasional reads on each
    request to verify tokens or fetch config), SQLite should handle this
    load easily. Each MCP server typically runs as a single Node process
    (no high contention multi-process writes). By using a **persistent
    volume** (the user mentioned a bind mount with ample disk space),
    data will survive container restarts similarly to a Postgres
    container volume. Ensuring the SQLite database is on reliable
    storage is important (to avoid corruption on abrupt shutdowns, etc.,
    though SQLite is robust if used properly). For backup/maintenance,
    the SQLite file can be copied or accessed directly as needed,
    simplifying operations compared to running a Postgres service.

**Summary of Migration Steps:** To implement the switch, one would:

1.  **Introduce SQLite config** -- e.g. add an option like
    `DATABASE_URL=sqlite:///data/mcp.db` (or some flag) that the code
    can detect. In Personal Context MCP's case, set Prisma's provider to
    sqlite and update connection
    strings[\[44\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L8-L16).
    In others, initialize a SQLite database connection if an SQLite URL
    is given.
2.  **Apply Schema to SQLite** -- Convert and execute the DDL statements
    on the SQLite connection. This could be done with an automated
    migration tool or by embedding an adjusted `schema.sql`. For
    instance, change `JSONB` to `TEXT`, `UUID PRIMARY KEY` to
    `TEXT PRIMARY KEY`, and remove or modify complex index definitions
    not supported by SQLite (most standard indices will work as-is). The
    core tables and columns remain the same.
3.  **Update Query Logic** -- Modify repository functions and DB
    utilities to use the SQLite client. Remove any Postgres-specific
    code (e.g. the PG connection pool config and error handlers). Ensure
    that where Postgres required explicit casts or JSON handling, the
    logic is updated for SQLite (often simply not needed or handled in
    application code).
4.  **Test the OAuth flow extensively** -- Verify that client
    registration, authorization, and token exchange all work using
    SQLite. For example, run the provided DCR smoke test scripts against
    the new
    setup[\[45\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L94-L103)[\[46\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L106-L114).
    The expected outcome is identical: the client can register, get an
    auth code via `/authorize`, exchange it at `/token` for a token, and
    use that token at `/mcp`. Any failures might indicate a query or
    schema mismatch to fix.
5.  **Deployment** -- Build the Docker image to include the SQLite
    database file path and remove the Postgres service dependency. The
    container can mount a host directory (for persistence). This
    simplifies deployment to a single container per MCP server. Each
    server's Dockerfile may need adjustment to include the SQLite binary
    or client library, but SQLite's library is lightweight. Environment
    variable management becomes simpler (no need for
    `POSTGRES_PASSWORD`, etc., just a path or default for the SQLite
    DB).

By following this migration path, the MCP servers should retain all
functionality -- **OAuth identification flows, dynamic client
registration, caching, encryption** -- while eliminating the external
database component. This will likely resolve the "failed DB connections"
issues (e.g. HTTP 500 errors due to network DB outages) because the
database is now local to the app. In effect, using SQLite trades off
some scalability of Postgres for improved simplicity and reliability in
a single-node context, which seems appropriate given the deployment
constraints (Docker on a single host with persistent volumes). The core
logic of managing sessions and credentials remains unchanged; only the
storage engine differs.

Overall, migrating to a file-based DB aligns with the project's goals of
easy local/self-contained deployment -- it **removes one moving part
(the Postgres container)** while maintaining data integrity and the
security model already in place (encryption via `MASTER_KEY`, token
hashing, etc.). With careful implementation, the MCP servers will
continue to meet the Model Context Protocol standards for OAuth 2.0
support and client registration, now backed by an embedded database that
simplifies deployment and reduces the chance of runtime configuration
errors.

**Sources:**

-   ClickUp MCP README -- OAuth2 flows and Dynamic Client
    Registration[\[2\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L135-L143)[\[19\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L248-L257)
-   Google Workspace MCP README -- environment config
    (PostgreSQL)[\[26\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L52-L60)[\[25\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L36-L44)
-   Personal Context MCP README -- OAuth & DCR support; Postgres
    requirement[\[47\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L15)[\[27\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L26)
-   ClickUp MCP Schema (PostgreSQL
    DDL)[\[28\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L10)[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46)
-   ClickUp MCP Auth Router -- `/register` and `/token`
    implementation[\[3\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L58-L67)[\[16\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L220-L229)
-   Google Workspace MCP Server -- OAuth endpoints and token
    exchange[\[48\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L371-L378)[\[14\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L577-L586)
-   Personal Context MCP Prisma Schema -- Models for OAuth (Client,
    AuthCode, Session,
    etc.)[\[8\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L60-L68)[\[49\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L91-L100)

------------------------------------------------------------------------

[\[1\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L11)
[\[27\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L19-L26)
[\[45\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L94-L103)
[\[46\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L106-L114)
[\[47\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md#L7-L15)
README.md

<https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/README.md>

[\[2\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md#L135-L143)
README.md

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/README.md>

[\[3\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L58-L67)
[\[4\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L95-L103)
[\[5\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L74-L83)
[\[6\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L98-L106)
[\[9\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L207-L215)
[\[10\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L199-L208)
[\[11\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L210-L218)
[\[16\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts#L220-L229)
authRouter.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/authRouter.ts>

[\[7\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L370-L378)
[\[12\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L545-L554)
[\[13\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L571-L580)
[\[14\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L577-L586)
[\[15\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L588-L595)
[\[17\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L582-L590)
[\[22\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L109-L116)
[\[23\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L129-L133)
[\[43\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L576-L585)
[\[48\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts#L371-L378)
server.ts

<https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/src/server.ts>

[\[8\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L60-L68)
[\[38\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L76-L84)
[\[44\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L8-L16)
[\[49\]](https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma#L91-L100)
schema.prisma

<https://github.com/polaralias/personal-context-mcp/blob/81e5eb1ea101621d364cdfcef3dac94db3c74885/prisma/schema.prisma>

[\[18\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L248-L256)
[\[19\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L248-L257)
[\[20\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L224-L232)
[\[21\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L250-L258)
[\[32\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L58-L67)
[\[33\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L72-L80)
[\[41\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts#L100-L108)
index.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/server/index.ts>

[\[24\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L10-L18)
[\[25\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L36-L44)
[\[35\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L40-L48)
[\[36\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml#L42-L45)
docker-compose.yml

<https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/docker-compose.yml>

[\[26\]](https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md#L52-L60)
README.md

<https://github.com/polaralias/google-workspace-mcp/blob/8b98621b7a7adfc1aa2ee43909228a297d2b5ada/README.md>

[\[28\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L10)
[\[29\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L38-L46)
[\[30\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L1-L9)
[\[31\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql#L18-L26)
schema.sql

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/schema.sql>

[\[34\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts#L10-L18)
index.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/db/index.ts>

[\[37\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L14-L19)
[\[40\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts#L11-L19)
ClientRepository.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/ClientRepository.ts>

[\[39\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/CacheRepository.ts#L14-L22)
CacheRepository.ts

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/src/infrastructure/repositories/CacheRepository.ts>

[\[42\]](https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docs/design/local_deployment.md#L98-L105)
local_deployment.md

<https://github.com/polaralias/clickup-mcp/blob/ceb1ac5d1bafb5e7b610e497cf611fa5a2d54961/docs/design/local_deployment.md>
