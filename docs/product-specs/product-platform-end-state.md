# Product And Platform End State

This file now records the achieved publish boundary for `google-workspace-mcp`.

## Product Contract

The public product is:

- one standalone FastMCP HTTP server
- one manifest-defined public interface limited to verified tools
- one explicit auth contract across OAuth, API key, and Keep master token
- one support matrix that states what is working and what is only narrowly supported

Users should be able to answer, from docs alone:

- which runtime path is supported
- which auth mode fits their use case
- which tools are public and supported
- which capabilities are intentionally excluded from the product contract

## Platform Contract

The platform is complete enough for public use because it now provides:

- a reliable local execution path through `uv run`
- a working Docker and Docker Compose deployment path
- non-live contract coverage for startup, auth, manifests, tool docs, Docker assumptions, and repaired regressions
- opt-in live integration coverage for every public OAuth-backed tool family
- explicit separation between public manifests and internal non-public runtime code

## Support Policy

Public support claims use only:

- `verified working`
- `verified limited`
- `known broken`
- `untested`

The current public surface contains only `verified working` and `verified limited` tools.

## Auth Contract

- OAuth is the primary Google Workspace auth story.
- API key support is intentionally narrow and public-read only.
- Keep support is master-token-only and separate from the OAuth-backed Workspace surface.
- Service-account and impersonation stories are not part of the supported product.

## Readiness Rule

The repository is publish-ready when a fresh contributor can answer these questions from tracked artefacts:

- What is the supported runtime path?
- Which auth modes are first-class?
- Which tools are public?
- Which tests protect the public contract?

That condition is now satisfied by the README, configuration guide, support matrix, per-tool matrix, architecture doc, and test suite.
