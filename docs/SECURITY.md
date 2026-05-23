# Security

## Security Principles

- secrets stay out of version control
- auth modes stay explicitly separated
- public-read access is not conflated with user-scoped OAuth access
- destructive validation targets only harness-owned artifacts

## Current Security Contract

- `.oauth/` and `.env` remain git-ignored
- MCP bearer-token auth is available for the HTTP endpoint
- OAuth, API key, and Keep master token are the only supported Google auth stories
- service-account and impersonation language has been removed from the public contract

## Sensitive Paths

- Keep master-token access is high sensitivity and should be limited to trusted environments
- API keys should be treated as scoped public-read credentials, not as a substitute for OAuth
- OAuth credential files should be stored only in the configured credential directory and never committed

## Validation Rules

- live tests create and clean up their own Workspace artifacts
- Docker validation is health-only by default
- support claims must stay aligned with the support matrix and per-tool matrix
