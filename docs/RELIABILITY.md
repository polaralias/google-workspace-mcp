# Reliability

## Current Reliability Contract

Reliable today:

- `uv run` startup and helper commands
- MCP health routes
- manifest registration for the public 53-tool surface
- OAuth credential loading
- Docker Compose startup and `/health`
- live OAuth-backed validation for every public Workspace family
- live API-key validation for the documented public-read subset
- Keep portability and core note-contract coverage

## Coverage Shape

Non-live contract coverage protects:

- auth and health surfaces
- manifest and runtime inventory alignment
- generated support artefacts
- repaired Drive file create/content behaviour
- Keep delete semantics
- Docker assumptions and container health

Opt-in live coverage protects:

- Calendar and calendar ACL
- Tasks
- Drive
- Docs
- Slides
- Sheets values
- Contacts
- Gmail search and filters
- Forms
- Meet conference records
- Keep master-token core flows
- API-key public-read flows

## Reliability Boundary

- `uv run` is the supported local runtime path.
- Public manifests contain only verified or verified-limited tools.
- Live test warning noise has been reduced but not fully eliminated; warnings do not currently mask failing tests.

## Canonical Evidence

- [product-specs/support-matrix.md](docs\product-specs\support-matrix.md)
- [generated/tool-support-matrix.md](docs\generated\tool-support-matrix.md)
- [validation-report-2026-05-16.md](docs\validation-report-2026-05-16.md)
