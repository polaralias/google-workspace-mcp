# AGENTS

## Purpose

This repository is a Google Workspace MCP server. The product is the integration server itself, not a user-facing web app.

## Current reality

- The runtime is centered on `server.py`.
- Tool surfaces are declared in `tool_manifest_google*.json`.
- Verified support status, known defects, and target harness outcomes are documented under `docs/`.
- The reliable local execution path is through `uv run`.

## Working rules

- Treat manifests as declared interface, not proof of behavior.
- Treat generated docs as secondary to live validation.
- Do not widen public claims without verification.
- Prefer adding tests and support-matrix evidence before refactors.
- Keep auth-mode behavior explicit: OAuth, API key, and Keep master token are the active support stories.

## First references to read

- [GLOSSARY.md](GLOSSARY.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/product-specs/product-platform-end-state.md](docs\product-specs\product-platform-end-state.md)
- [docs/product-specs/support-matrix.md](docs\product-specs\support-matrix.md)
- [docs/validation-report-2026-05-16.md](docs\validation-report-2026-05-16.md)
- [docs/PLANS.md](docs\PLANS.md)
- [docs/RELIABILITY.md](docs\RELIABILITY.md)
- [docs/SECURITY.md](docs\SECURITY.md)
- [docs/generated/tool-support-matrix.md](docs\generated\tool-support-matrix.md)
