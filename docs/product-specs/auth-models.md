---
type: "Product Contract"
title: "Auth Models"
description: "Documents Auth Models for the google-workspace-mcp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - google-workspace-mcp
  - product-contract
navigation:
  role: foundational
  order: 20
---
# Auth Models

This document defines the supported auth stories for `google-workspace-mcp`.

## MCP Client Auth

Purpose:

- protect the MCP HTTP endpoint

Current contract:

- static bearer-token auth via `GOOGLE_WORKSPACE_MCP_API_KEY`, `MCP_API_KEY`, or `MCP_API_KEYS`
- `API_KEY_MODE=disabled` is the explicit opt-out
- covered by [tests/test_auth_contract.py](tests\test_auth_contract.py)

## Stored OAuth

Purpose:

- primary auth for user-scoped Google Workspace operations

Current contract:

- stored credentials are loaded from `.oauth/` or `GOOGLE_MCP_CREDENTIALS_DIR`
- `GOOGLE_DEFAULT_USER_EMAIL` can provide the default user context
- the public Workspace tool surface is primarily verified through this path

Evidence:

- [tests/test_auth_contract.py](tests\test_auth_contract.py)
- [tests/test_credential_store_contract.py](tests\test_credential_store_contract.py)
- `tests/test_live_*_contract.py` for public OAuth-backed families

## API Key

Purpose:

- narrow public-read compatibility path

Current contract:

- only the documented public Drive permissions, Sheets metadata, and Slides PDF export stories are supported
- API-key presence does not imply general Workspace access

Evidence:

- [tests/test_live_public_api_key_contract.py](tests\test_live_public_api_key_contract.py)
- [docs/validation-report-2026-05-16.md](docs\validation-report-2026-05-16.md)

## Keep Master Token

Purpose:

- only supported Google Keep path

Current contract:

- requires `GOOGLE_KEEP_EMAIL` and `GOOGLE_KEEP_MASTER_TOKEN`
- supports Keep note CRUD plus label listing through the public manifests
- `gkeepapi` is loaded lazily so non-Keep startup paths remain portable

Evidence:

- [tests/test_keep_contract.py](tests\test_keep_contract.py)
- [tests/test_keep_portability_contract.py](tests\test_keep_portability_contract.py)
- [tests/test_live_keep_master_token_contract.py](tests\test_live_keep_master_token_contract.py)

## Repository knowledge

- [Documentation map](../knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
