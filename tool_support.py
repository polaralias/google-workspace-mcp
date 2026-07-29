from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from calendar_dispatch import CALENDAR_TOOL_NAMES
from contacts_dispatch import CONTACTS_TOOL_NAMES
from docs_dispatch import DOCS_TOOL_NAMES
from drive_dispatch import DRIVE_TOOL_NAMES
from forms_dispatch import FORMS_TOOL_NAMES
from gmail_dispatch import GMAIL_TOOL_NAMES
from keep_dispatch import KEEP_TOOL_NAMES
from manifest_support import repo_root
from meet_dispatch import MEET_TOOL_NAMES
from sheets_dispatch import SHEETS_TOOL_NAMES
from slides_dispatch import SLIDES_TOOL_NAMES
from tasks_dispatch import TASKS_TOOL_NAMES

ALLOWED_SUPPORT_STATUSES = {
    "verified working",
    "verified limited",
    "known broken",
    "untested",
}

DEFAULT_EVIDENCE = "manifest plus runtime only"
DEFAULT_LAST_VALIDATION = "none"
DEFAULT_EVIDENCE_TYPE = "none"
DEFAULT_LIMITATION = "Declared inventory only. No live or non-live support evidence is recorded for this tool yet."


def _repo_root() -> Path:
    return repo_root(__file__)


def manifest_tool_specs() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in sorted(_repo_root().glob("tool_manifest_google*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for spec in data.get("tools") or []:
            name = str((spec or {}).get("name") or "").strip()
            if not name:
                continue
            merged[name] = {**spec, "source_manifest": path.name}
    return merged


def manifest_tool_names() -> set[str]:
    return set(manifest_tool_specs())


def runtime_tool_names() -> set[str]:
    return (
        set(CALENDAR_TOOL_NAMES)
        | set(CONTACTS_TOOL_NAMES)
        | set(DOCS_TOOL_NAMES)
        | set(DRIVE_TOOL_NAMES)
        | set(FORMS_TOOL_NAMES)
        | set(GMAIL_TOOL_NAMES)
        | set(KEEP_TOOL_NAMES)
        | set(MEET_TOOL_NAMES)
        | set(SHEETS_TOOL_NAMES)
        | set(SLIDES_TOOL_NAMES)
        | set(TASKS_TOOL_NAMES)
    )


def _default_auth_mode(tool_name: str) -> str:
    if tool_name in KEEP_TOOL_NAMES:
        return "Keep master token"
    return "OAuth"


def _default_row(tool_name: str, manifest_source: str) -> dict[str, str]:
    return {
        "tool_name": tool_name,
        "manifest_source": manifest_source,
        "auth_mode": _default_auth_mode(tool_name),
        "status": "untested",
        "evidence_source": DEFAULT_EVIDENCE,
        "last_validation_date": DEFAULT_LAST_VALIDATION,
        "evidence_type": DEFAULT_EVIDENCE_TYPE,
        "known_limitations": DEFAULT_LIMITATION,
    }


def _apply(rows: dict[str, dict[str, str]], tool_names: list[str], **fields: str) -> None:
    for tool_name in tool_names:
        if tool_name not in rows:
            continue
        rows[tool_name].update(fields)


def tool_support_rows() -> list[dict[str, str]]:
    manifest = manifest_tool_specs()
    rows = {
        tool_name: _default_row(tool_name, f"`{spec.get('source_manifest', 'tool_manifest_google.json')}`")
        for tool_name, spec in manifest.items()
    }

    _apply(
        rows,
        ["list_calendars", "get_events", "create_event", "delete_event"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_calendar_contract.py](tests/test_live_calendar_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated with owned-artefact create/get/delete coverage on a real calendar.",
    )
    _apply(
        rows,
        ["get_free_busy", "list_calendar_acl", "create_calendar_acl_rule", "delete_calendar_acl_rule"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_calendar_acl_contract.py](tests/test_live_calendar_acl_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated on a disposable calendar created directly for the live harness.",
    )
    _apply(
        rows,
        ["list_task_lists", "create_task_list", "delete_task_list", "list_tasks", "create_task", "update_task", "delete_task"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_tasks_contract.py](tests/test_live_tasks_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated with owned task-list and task cleanup.",
    )
    _apply(
        rows,
        ["list_drive_items", "create_drive_folder", "create_drive_file", "get_drive_file_content", "delete_drive_file", "search_drive_files"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_drive_contract.py](tests/test_live_drive_contract.py), [tests/test_drive_contract.py](tests/test_drive_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated on owned folders and files. `get_drive_file_content` also has public API-key coverage for plain text files.",
    )
    _apply(
        rows,
        ["get_drive_file_permissions"],
        auth_mode="API key (public Drive files)",
        status="verified limited",
        evidence_source="[tests/test_live_public_api_key_contract.py](tests/test_live_public_api_key_contract.py), [docs/validation-report-2026-05-16.md](docs/validation-report-2026-05-16.md)",
        last_validation_date="2026-05-23",
        evidence_type="manual + automated",
        known_limitations="Validated only for public-file permission reads in API-key mode.",
    )
    _apply(
        rows,
        ["create_doc", "get_doc_content", "modify_doc_text"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_docs_contract.py](tests/test_live_docs_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated on owned Google Docs with Drive-based cleanup.",
    )
    _apply(
        rows,
        ["create_presentation", "get_presentation", "create_slide"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_slides_contract.py](tests/test_live_slides_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated on owned presentations with Drive-based cleanup.",
    )
    _apply(
        rows,
        ["export_presentation_pdf"],
        auth_mode="API key (public presentations)",
        status="verified limited",
        evidence_source="[tests/test_live_public_api_key_contract.py](tests/test_live_public_api_key_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated only for public presentation export in API-key mode.",
    )
    _apply(
        rows,
        ["modify_sheet_values", "append_sheet_rows", "batch_update_sheet_values", "read_sheet_values", "batch_get_sheet_values"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_sheets_contract.py](tests/test_live_sheets_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated on disposable spreadsheets with Drive cleanup.",
    )
    _apply(
        rows,
        ["get_spreadsheet_info"],
        auth_mode="API key (public spreadsheets)",
        status="verified limited",
        evidence_source="[tests/test_live_public_api_key_contract.py](tests/test_live_public_api_key_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated only for public spreadsheets in API-key mode.",
    )
    _apply(
        rows,
        ["search_gmail_messages"],
        auth_mode="OAuth",
        status="verified limited",
        evidence_source="[tests/test_live_gmail_contract.py](tests/test_live_gmail_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Only read-only message search is validated. This should not be generalised to message-content or mutation wrappers.",
    )
    _apply(
        rows,
        ["list_gmail_filters", "create_gmail_filter", "delete_gmail_filter"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_gmail_filters_contract.py](tests/test_live_gmail_filters_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated with owned filter lifecycle coverage.",
    )
    _apply(
        rows,
        ["archive_gmail_message", "trash_gmail_message", "mark_gmail_read_unread", "star_unstar_gmail_message"],
        auth_mode="OAuth",
        status="untested",
        evidence_source=DEFAULT_EVIDENCE,
        last_validation_date=DEFAULT_LAST_VALIDATION,
        evidence_type=DEFAULT_EVIDENCE_TYPE,
        known_limitations="Message-mutation wrappers are declared inventory only until an owned-artifact Gmail mutation harness exists.",
    )
    _apply(
        rows,
        ["get_gmail_message_content", "get_gmail_messages_content_batch", "get_gmail_attachment_content"],
        auth_mode="OAuth",
        status="untested",
        evidence_source=DEFAULT_EVIDENCE,
        last_validation_date=DEFAULT_LAST_VALIDATION,
        evidence_type=DEFAULT_EVIDENCE_TYPE,
        known_limitations="Gmail content and attachment reads are not yet live-validated through the public wrapper surface.",
    )
    _apply(
        rows,
        ["list_contacts", "create_contact", "update_contact", "delete_contact"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_contacts_contract.py](tests/test_live_contacts_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated with owned contact CRUD cleanup.",
    )
    _apply(
        rows,
        ["search_contacts"],
        auth_mode="OAuth",
        status="verified limited",
        evidence_source="[tests/test_live_contacts_contract.py](tests/test_live_contacts_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Supports prefix search after the required People API warmup request. Immediate read-after-write visibility should not be assumed outside that cache-refresh contract.",
    )
    _apply(
        rows,
        ["batch_update_form"],
        auth_mode="OAuth",
        status="verified working",
        evidence_source="[tests/test_live_forms_contract.py](tests/test_live_forms_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated on disposable forms with Drive cleanup.",
    )
    _apply(
        rows,
        ["list_conference_records", "get_conference_record"],
        auth_mode="OAuth",
        status="verified limited",
        evidence_source="[tests/test_live_meet_contract.py](tests/test_live_meet_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Read-only probe only. `get_conference_record` is exercised when the account has accessible records.",
    )
    _apply(
        rows,
        ["list_keep_notes", "get_keep_note", "create_keep_note", "delete_keep_note", "list_keep_labels", "update_keep_note"],
        auth_mode="Keep master token",
        status="verified working",
        evidence_source="[tests/test_live_keep_master_token_contract.py](tests/test_live_keep_master_token_contract.py), [tests/test_keep_contract.py](tests/test_keep_contract.py), [tests/test_keep_portability_contract.py](tests/test_keep_portability_contract.py)",
        last_validation_date="2026-05-23",
        evidence_type="automated",
        known_limitations="Validated through the master-token path for list, create, read, update, delete, and label listing on owned Keep artefacts.",
    )
    ordered_rows = [rows[name] for name in sorted(rows)]
    for row in ordered_rows:
        if row["status"] not in ALLOWED_SUPPORT_STATUSES:
            raise ValueError(f"unsupported support status for {row['tool_name']}: {row['status']}")
    return ordered_rows


def public_tool_names() -> set[str]:
    return {row["tool_name"] for row in tool_support_rows() if row["status"] != "untested"}


def render_tool_support_matrix() -> str:
    lines = [
        "# Per-Tool Support Matrix",
        "",
        "This artefact is generated from the manifest inventory and curated support metadata in `tool_support.py`.",
        "",
        "Interpretation rules:",
        "- This file is inventory plus support metadata, not a claim that every declared tool is safe to use.",
        "- Use [../product-specs/support-matrix.md](../product-specs/support-matrix.md) for the family-level summary and policy rules.",
        "",
        "| Tool | Declared in | Auth mode | Status | Evidence | Last validation | Evidence type | Known limitations |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in tool_support_rows():
        lines.append(
            "| {tool_name} | {manifest_source} | {auth_mode} | `{status}` | {evidence_source} | {last_validation_date} | {evidence_type} | {known_limitations} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)
