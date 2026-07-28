---
type: "Product Contract"
title: "Verified Support Matrix"
description: "Documents Verified Support Matrix for the google-workspace-mcp repository."
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
# Verified Support Matrix

This document is the canonical product contract for `google-workspace-mcp`.

Use it to answer:

- which public tool families are supported today
- which auth mode each family requires
- what evidence backs the claim
- where the verified boundary stops

The per-tool companion is [../generated/tool-support-matrix.md](../generated/tool-support-matrix.md).

## Status Vocabulary

Support claims use:

- `verified working`
- `verified limited`
- `known broken`
- `untested`

The current public contract uses only `verified working` and `verified limited`. Previously unverified wrappers were removed from the manifests instead of being published as active tools.

## Current Family-Level Support

| Product family | Public tools | Auth mode | Status | Evidence | Last validation | Evidence type | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Server startup and health | manifest registration, health routes, supported auth reporting | none plus MCP bearer auth when enabled | `verified working` | [tests/test_smoke_contract.py](tests\test_smoke_contract.py), [tests/test_auth_contract.py](tests\test_auth_contract.py), [tests/test_run_server_contract.py](tests\test_run_server_contract.py), [tests/test_docker_contract.py](tests\test_docker_contract.py) | 2026-05-23 | automated | Verified locally through `uv run` and Docker Compose health smoke. |
| OAuth credential loading | stored credential load and refresh path | OAuth | `verified working` | [tests/test_auth_contract.py](tests\test_auth_contract.py), [tests/test_credential_store_contract.py](tests\test_credential_store_contract.py) | 2026-05-23 | automated | This is the primary Google Workspace auth story. |
| Calendar | `list_calendars`, `get_events`, `create_event`, `delete_event` | OAuth | `verified working` | [tests/test_live_calendar_contract.py](tests\test_live_calendar_contract.py) | 2026-05-23 | automated | Owned-artefact lifecycle revalidated in the current workspace. |
| Calendar free/busy and ACL | `get_free_busy`, `list_calendar_acl`, `create_calendar_acl_rule`, `delete_calendar_acl_rule` | OAuth | `verified working` | [tests/test_live_calendar_acl_contract.py](tests\test_live_calendar_acl_contract.py) | 2026-05-23 | automated | Validated on a disposable calendar created by the live harness. |
| Tasks | `list_task_lists`, `create_task_list`, `delete_task_list`, `list_tasks`, `create_task`, `update_task`, `delete_task` | OAuth | `verified working` | [tests/test_live_tasks_contract.py](tests\test_live_tasks_contract.py) | 2026-05-23 | automated | Owned task-list and task cleanup is enforced by the live harness. |
| Drive | `search_drive_files`, `list_drive_items`, `create_drive_folder`, `create_drive_file`, `get_drive_file_content`, `delete_drive_file` | OAuth | `verified working` | [tests/test_drive_contract.py](tests\test_drive_contract.py), [tests/test_live_drive_contract.py](tests\test_live_drive_contract.py) | 2026-05-23 | automated | Includes regression coverage for file create and plain-file content reads. |
| Drive public permissions | `get_drive_file_permissions` | API key | `verified limited` | [tests/test_live_public_api_key_contract.py](tests\test_live_public_api_key_contract.py), [docs/validation-report-2026-05-16.md](docs\validation-report-2026-05-16.md) | 2026-05-23 | manual + automated | Verified only for public Drive files in API-key mode. |
| Docs | `create_doc`, `get_doc_content`, `modify_doc_text` | OAuth | `verified working` | [tests/test_live_docs_contract.py](tests\test_live_docs_contract.py) | 2026-05-23 | automated | Validated on owned documents with Drive cleanup. |
| Slides | `create_presentation`, `get_presentation`, `create_slide` | OAuth | `verified working` | [tests/test_live_slides_contract.py](tests\test_live_slides_contract.py) | 2026-05-23 | automated | Validated on owned presentations with Drive cleanup. |
| Slides public export | `export_presentation_pdf` | API key | `verified limited` | [tests/test_live_public_api_key_contract.py](tests\test_live_public_api_key_contract.py), [docs/validation-report-2026-05-16.md](docs\validation-report-2026-05-16.md) | 2026-05-23 | manual + automated | Limited to public presentations in API-key mode. |
| Sheets values | `modify_sheet_values`, `append_sheet_rows`, `batch_update_sheet_values`, `read_sheet_values`, `batch_get_sheet_values` | OAuth | `verified working` | [tests/test_live_sheets_contract.py](tests\test_live_sheets_contract.py) | 2026-05-23 | automated | Validated on disposable spreadsheets with Drive cleanup. |
| Sheets public read | `get_spreadsheet_info` | API key | `verified limited` | [tests/test_live_public_api_key_contract.py](tests\test_live_public_api_key_contract.py), [docs/validation-report-2026-05-16.md](docs\validation-report-2026-05-16.md) | 2026-05-23 | manual + automated | Limited to public spreadsheets in API-key mode. |
| Gmail search | `search_gmail_messages` | OAuth | `verified limited` | [tests/test_live_gmail_contract.py](tests\test_live_gmail_contract.py) | 2026-05-23 | automated | Read-only message search only. |
| Gmail filters | `list_gmail_filters`, `create_gmail_filter`, `delete_gmail_filter` | OAuth | `verified working` | [tests/test_live_gmail_filters_contract.py](tests\test_live_gmail_filters_contract.py) | 2026-05-23 | automated | Owned filter lifecycle revalidated in the current workspace. |
| Contacts CRUD | `list_contacts`, `create_contact`, `update_contact`, `delete_contact` | OAuth | `verified working` | [tests/test_live_contacts_contract.py](tests\test_live_contacts_contract.py) | 2026-05-23 | automated | Validated with owned contact cleanup. |
| Contacts search | `search_contacts` | OAuth | `verified limited` | [tests/test_live_contacts_contract.py](tests\test_live_contacts_contract.py), [tests/test_domain_dispatch_contract.py](tests\test_domain_dispatch_contract.py) | 2026-05-23 | automated | Supported for prefix search after the required People API warmup request. Immediate read-after-write visibility is not part of the contract. |
| Forms | `batch_update_form` | OAuth | `verified working` | [tests/test_live_forms_contract.py](tests\test_live_forms_contract.py) | 2026-05-23 | automated | Validated on disposable forms. |
| Meet conference records | `list_conference_records`, `get_conference_record` | OAuth | `verified limited` | [tests/test_live_meet_contract.py](tests\test_live_meet_contract.py) | 2026-05-23 | automated | Read-only probe; `get_conference_record` is exercised when records are available. |
| Keep notes and labels | `list_keep_notes`, `get_keep_note`, `create_keep_note`, `update_keep_note`, `delete_keep_note`, `list_keep_labels` | Keep master token | `verified working` | [tests/test_keep_contract.py](tests\test_keep_contract.py), [tests/test_keep_portability_contract.py](tests\test_keep_portability_contract.py), [tests/test_live_keep_master_token_contract.py](tests\test_live_keep_master_token_contract.py) | 2026-05-23 | automated | Supported only through the unofficial Keep master-token path. |

## Contract Rules

- Manifest presence is public interface, not proof by itself.
- Public manifests now exclude previously unverified wrappers.
- `verified limited` means the boundary is intentionally narrow and must not be generalised.
- Historical evidence remains in dated reports; current support claims belong here first.

## Excluded Capability Rule

If a tool is not listed in the public manifests or the per-tool matrix, it is not part of the supported product contract even if an internal dispatcher still contains code for it.

## Repository knowledge

- [Documentation map](../knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
