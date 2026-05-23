
from __future__ import annotations

import base64
import hashlib
import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from auth_support import CredentialStore, StaticApiKeyVerifier, _load_api_keys, _runtime_env
from calendar_dispatch import CALENDAR_TOOL_NAMES, dispatch_calendar as _dispatch_calendar_impl
from contacts_dispatch import CONTACTS_TOOL_NAMES, dispatch_contacts as _dispatch_contacts_impl
from docs_dispatch import DOCS_TOOL_NAMES, dispatch_docs as _dispatch_docs_impl
from drive_dispatch import DRIVE_TOOL_NAMES, dispatch_drive as _dispatch_drive_impl, resolve_drive_item as _resolve_drive_item_impl, resolve_folder as _resolve_folder_impl
from fastmcp import FastMCP
from forms_dispatch import FORMS_TOOL_NAMES, dispatch_forms as _dispatch_forms_impl
from gmail_dispatch import GMAIL_TOOL_NAMES, dispatch_gmail as _dispatch_gmail_impl
from keep_dispatch import KEEP_TOOL_NAMES, dispatch_keep_master_token as _dispatch_keep_master_token_impl
from meet_dispatch import MEET_TOOL_NAMES, dispatch_meet as _dispatch_meet_impl
from googleapiclient.discovery import build
from manifest_support import load_manifest as _load_manifest_impl, register_tools as _register_tools_impl, repo_root as _repo_root_impl
import requests
from sheets_dispatch import SHEETS_TOOL_NAMES, dispatch_sheets as _dispatch_sheets_impl
from slides_dispatch import SLIDES_TOOL_NAMES, dispatch_slides as _dispatch_slides_impl
from starlette.responses import JSONResponse
from tasks_dispatch import TASKS_TOOL_NAMES, dispatch_tasks as _dispatch_tasks_impl

KEEP_MANAGED_LABEL_DEFAULT = "google-workspace-mcp"
KEEP_MANAGED_LABEL_LEGACY = "google-workspace-fast-mcp"
MASTER_TOKEN_KEEP_TOOL_NAMES = {
    "list_keep_notes",
    "get_keep_note",
    "create_keep_note",
    "delete_keep_note",
    "download_keep_attachment",
    "share_keep_note",
    "unshare_keep_note",
    "get_keep_note_permissions",
    "find_keep_notes",
    "create_keep_list",
    "update_keep_note",
    "add_keep_list_item",
    "update_keep_list_item",
    "delete_keep_list_item",
    "set_keep_note_color",
    "pin_keep_note",
    "archive_keep_note",
    "trash_keep_note",
    "restore_keep_note",
    "list_keep_labels",
    "create_keep_label",
    "delete_keep_label",
    "add_keep_label_to_note",
    "remove_keep_label_from_note",
    "list_keep_note_collaborators",
    "add_keep_note_collaborator",
    "remove_keep_note_collaborator",
    "list_keep_note_media",
}
_GKEEPAPI_MODULE: Any | None = None
def _load_gkeepapi() -> Any:
    global _GKEEPAPI_MODULE
    if _GKEEPAPI_MODULE is not None:
        return _GKEEPAPI_MODULE
    try:
        _GKEEPAPI_MODULE = importlib.import_module("gkeepapi")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "gkeepapi is required for Google Keep master-token tools. "
            "Install the project dependencies through uv to enable that path."
        ) from exc
    return _GKEEPAPI_MODULE
def _repo_root() -> Path:
    return _repo_root_impl(__file__)


def _load_manifest() -> list[dict[str, Any]]:
    return _load_manifest_impl(_repo_root())
def _normalize_keep_note_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("note_name is required")
    if text.startswith("notes/"):
        return text.split("/", 1)[1]
    return text


def _keep_note_resource_name(note_id: str) -> str:
    return f"notes/{note_id}"


def _page_slice(items: list[Any], page_size: Any, page_token: Any) -> tuple[list[Any], str | None]:
    try:
        size = max(1, min(int(page_size or 25), 250))
    except (TypeError, ValueError):
        size = 25
    try:
        start = max(0, int(str(page_token or "0").strip() or "0"))
    except ValueError:
        start = 0
    end = start + size
    next_token = str(end) if end < len(items) else None
    return items[start:end], next_token


class GoogleKeepMasterTokenBackend:
    def __init__(self, default_user_email: str = "") -> None:
        configured_email = _runtime_env("GOOGLE_KEEP_EMAIL", default=default_user_email)
        self._email = configured_email.strip().lower()
        self._master_token = _runtime_env("GOOGLE_KEEP_MASTER_TOKEN")
        self._managed_label_name = _runtime_env("GOOGLE_KEEP_MANAGED_LABEL", default=KEEP_MANAGED_LABEL_DEFAULT).strip() or KEEP_MANAGED_LABEL_DEFAULT
        self._unsafe_mode = _runtime_env("GOOGLE_KEEP_UNSAFE_MODE", "UNSAFE_MODE", default="false").lower() == "true"
        self._client: gkeepapi.Keep | None = None
        self._authenticated_email = ""

    @property
    def configured(self) -> bool:
        return bool(self._master_token and self._email)

    @property
    def email(self) -> str:
        return self._email

    @property
    def managed_label_names(self) -> tuple[str, ...]:
        names = [self._managed_label_name]
        if self._managed_label_name != KEEP_MANAGED_LABEL_LEGACY:
            names.append(KEEP_MANAGED_LABEL_LEGACY)
        return tuple(dict.fromkeys(name for name in names if name))

    @property
    def managed_label_name(self) -> str:
        return self._managed_label_name

    @property
    def unsafe_mode(self) -> bool:
        return self._unsafe_mode

    def _effective_email(self, user_email: str | None) -> str:
        effective = str(user_email or self._email or "").strip().lower()
        if not effective:
            raise PermissionError(
                "Google Keep master-token access requires GOOGLE_KEEP_EMAIL or "
                "GOOGLE_DEFAULT_USER_EMAIL to be configured."
            )
        if self._email and effective != self._email:
            raise PermissionError(
                f"Google Keep master-token access is configured for {self._email}, "
                f"not {effective}."
            )
        return effective

    def client(self, user_email: str | None = None) -> gkeepapi.Keep:
        effective = self._effective_email(user_email)
        if not self._master_token:
            raise PermissionError(
                "Google Keep master-token access requires GOOGLE_KEEP_MASTER_TOKEN."
            )
        if self._client is not None and self._authenticated_email == effective:
            return self._client

        gkeepapi = _load_gkeepapi()
        keep = gkeepapi.Keep()
        try:
            keep.authenticate(effective, self._master_token)
        except requests.exceptions.JSONDecodeError as exc:
            raise RuntimeError(
                "Google Keep authentication returned a non-JSON response. "
                "The unofficial Keep endpoint may be blocked from this network "
                "or the master token may be invalid."
            ) from exc
        except gkeepapi.exception.LoginException as exc:
            raise RuntimeError(
                "Google Keep login failed. Verify GOOGLE_KEEP_EMAIL and "
                "GOOGLE_KEEP_MASTER_TOKEN."
            ) from exc

        self._client = keep
        self._authenticated_email = effective
        return keep

    def serialize_label(self, label: Any) -> dict[str, Any]:
        return {"id": label.id, "name": label.name}

    def serialize_list_item(self, item: Any) -> dict[str, Any]:
        parent_item = getattr(item, "parent_item", None)
        return {
            "id": item.id,
            "text": item.text,
            "checked": item.checked,
            "parentItemId": parent_item.id if parent_item else None,
        }

    def serialize_note(self, note: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": note.id,
            "name": _keep_note_resource_name(note.id),
            "title": note.title,
            "text": note.text,
            "type": note.type.value,
            "pinned": note.pinned,
            "archived": note.archived,
            "trashed": note.trashed,
            "color": note.color.value if note.color else None,
            "labels": [self.serialize_label(label) for label in note.labels.all()],
            "collaborators": list(note.collaborators.all()),
            "managedByMcp": self.has_managed_label(note),
        }
        if hasattr(note, "items"):
            payload["items"] = [self.serialize_list_item(item) for item in note.items]
        payload["media"] = [
            {
                "blobId": blob.id,
                "type": blob.blob.type.value if blob.blob and blob.blob.type else None,
            }
            for blob in note.blobs
        ]
        return payload

    def get_note_or_raise(self, user_email: str | None, note_name: Any) -> tuple[gkeepapi.Keep, Any]:
        keep = self.client(user_email)
        note_id = _normalize_keep_note_name(note_name)
        note = keep.get(note_id)
        if not note:
            raise ValueError(f"Note with ID {note_id} was not found")
        return keep, note

    def has_managed_label(self, note: Any) -> bool:
        return any(label.name in self.managed_label_names for label in note.labels.all())

    def ensure_modifiable(self, note: Any) -> None:
        if self._unsafe_mode or self.has_managed_label(note):
            return
        raise ValueError(
            f"Note {note.id} cannot be modified because it does not have the "
            f"'{self._managed_label_name}' label. Set GOOGLE_KEEP_UNSAFE_MODE=true "
            "to allow edits to existing notes."
        )

    def ensure_managed_label(self, keep: gkeepapi.Keep) -> Any:
        if self._unsafe_mode:
            return None
        label = keep.findLabel(self._managed_label_name)
        if label is None:
            label = keep.createLabel(self._managed_label_name)
        return label

    def resolve_label(self, keep: gkeepapi.Keep, label_ref: Any) -> Any:
        key = str(label_ref or "").strip()
        if not key:
            raise ValueError("label_id is required")
        label = keep.getLabel(key)
        if label is not None:
            return label
        label = keep.findLabel(key)
        if label is not None:
            return label
        raise ValueError(f"Label '{key}' was not found")

    def resolve_labels(self, keep: gkeepapi.Keep, labels: Any) -> list[Any] | None:
        values = _as_string_list(labels, "labels")
        if not values:
            return None
        return [self.resolve_label(keep, value) for value in values]

    def normalize_colors(self, colors: Any) -> list[Any] | None:
        values = _as_string_list(colors, "colors")
        if not values:
            return None
        gkeepapi = _load_gkeepapi()
        normalized: list[Any] = []
        for value in values:
            try:
                normalized.append(gkeepapi.node.ColorValue(value.upper()))
            except ValueError as exc:
                raise ValueError(f"Invalid Keep color '{value}'") from exc
        return normalized

    def list_media(self, user_email: str | None, note_name: Any) -> list[dict[str, Any]]:
        keep, note = self.get_note_or_raise(user_email, note_name)
        media: list[dict[str, Any]] = []
        for blob in note.blobs:
            media.append(
                {
                    "blobId": blob.id,
                    "type": blob.blob.type.value if blob.blob and blob.blob.type else None,
                    "mediaLink": keep.getMediaLink(blob),
                }
            )
        return media

    def find_blob(self, user_email: str | None, attachment_name: Any) -> tuple[Any, Any, str]:
        keep = self.client(user_email)
        lookup = str(attachment_name or "").strip()
        if not lookup:
            raise ValueError("attachment_name is required")
        attachment_id = lookup.rsplit("/", 1)[-1]
        for note in keep.all():
            for blob in note.blobs:
                if blob.id == attachment_id:
                    mime_type = blob.blob.type.value if blob.blob and blob.blob.type else "application/octet-stream"
                    return note, blob, mime_type
        raise ValueError(f"Attachment '{lookup}' was not found")


def _decode_b64url(value: str | None) -> str:
    if not value:
        return ""
    padded = value + "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")

def _extract_headers(headers: list[dict[str, Any]] | None, wanted: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    lookup = {w.lower(): w for w in wanted}
    for header in headers or []:
        name = str(header.get("name") or "")
        value = str(header.get("value") or "")
        key = lookup.get(name.lower())
        if key:
            found[key] = value
    return found


def _extract_bodies(payload: dict[str, Any]) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime_type = str(part.get("mimeType") or "")
        decoded = _decode_b64url((part.get("body") or {}).get("data"))
        if mime_type == "text/plain" and decoded:
            text_parts.append(decoded)
        elif mime_type == "text/html" and decoded:
            html_parts.append(decoded)
        for child in part.get("parts") or []:
            if isinstance(child, dict):
                walk(child)

    walk(payload)
    return ("\n".join(text_parts).strip(), "\n".join(html_parts).strip())


def _extract_doc_text(content: list[dict[str, Any]] | None) -> str:
    out: list[str] = []
    for element in content or []:
        paragraph = element.get("paragraph")
        if paragraph:
            for run in paragraph.get("elements") or []:
                text = ((run.get("textRun") or {}).get("content"))
                if text:
                    out.append(str(text))
        table = element.get("table")
        if table:
            for row in table.get("tableRows") or []:
                cells: list[str] = []
                for cell in row.get("tableCells") or []:
                    cells.append(_extract_doc_text(cell.get("content")))
                out.append("\t".join(cells))
    return "".join(out).strip()


def _extract_slide_text(slide: dict[str, Any]) -> str:
    lines: list[str] = []
    for element in slide.get("pageElements") or []:
        text_block = ((element.get("shape") or {}).get("text") or {})
        chunk: list[str] = []
        for te in text_block.get("textElements") or []:
            value = ((te.get("textRun") or {}).get("content"))
            if value:
                chunk.append(str(value))
        if chunk:
            lines.append("".join(chunk).strip())
    return "\n".join([line for line in lines if line])


def _load_jsonish(value: Any, label: str) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} must be valid JSON") from exc
    raise ValueError(f"{label} must be a JSON object, array, or JSON string")


def _as_dict(value: Any, label: str) -> dict[str, Any]:
    parsed = _load_jsonish(value, label)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def _as_list(value: Any, label: str) -> list[Any]:
    parsed = _load_jsonish(value, label)
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError(f"{label} must be a JSON array")
    return parsed


def _as_string_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        if cleaned.startswith("["):
            parsed = _as_list(cleaned, label)
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [cleaned]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise ValueError(f"{label} must be a string, array, or JSON array string")


def _normalize_attendees(value: Any) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    attendees = _as_list(value, "attendees") if isinstance(value, str) else value
    if not isinstance(attendees, list):
        raise ValueError("attendees must be a list")
    out: list[dict[str, Any]] = []
    for attendee in attendees:
        if isinstance(attendee, str):
            out.append({"email": attendee})
        elif isinstance(attendee, dict):
            out.append(attendee)
        else:
            raise ValueError("attendees entries must be strings or objects")
    return out


def _parse_reminders(value: Any) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    reminders = _as_list(value, "reminders") if isinstance(value, str) else value
    if not isinstance(reminders, list):
        raise ValueError("reminders must be a list")
    out: list[dict[str, Any]] = []
    for reminder in reminders[:5]:
        if not isinstance(reminder, dict):
            continue
        method = str(reminder.get("method") or "").strip()
        minutes = reminder.get("minutes")
        if method not in {"email", "popup"}:
            continue
        try:
            minutes_value = int(minutes)
        except (TypeError, ValueError):
            continue
        if 0 <= minutes_value <= 40320:
            out.append({"method": method, "minutes": minutes_value})
    return out


def _correct_time_format(value: str | None) -> str | None:
    if not value:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return f"{value}T00:00:00Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
        return f"{value}Z"
    return value


def _normalize_due(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{text}T00:00:00.000Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text):
        return f"{text}Z"
    return text


def _field_mask(*parts: str) -> str:
    return ",".join(part for part in parts if part)


def _json_export(raw: Any, mime_type: str) -> dict[str, Any]:
    if isinstance(raw, bytes):
        if mime_type.startswith("text/") or mime_type in {"application/json"}:
            return {
                "mimeType": mime_type,
                "content": raw.decode("utf-8", errors="replace"),
                "contentEncoding": "utf-8",
            }
        return {
            "mimeType": mime_type,
            "contentBase64": base64.b64encode(raw).decode("ascii"),
            "contentEncoding": "base64",
        }
    return {
        "mimeType": mime_type,
        "content": str(raw),
        "contentEncoding": "utf-8",
    }


def _optional_color(value: Any, label: str) -> dict[str, Any] | None:
    color = _as_dict(value, label)
    if not color:
        return None
    if "color" in color:
        return color
    if "rgbColor" in color:
        return {"color": {"rgbColor": color["rgbColor"]}}
    rgb: dict[str, float] = {}
    for channel in ("red", "green", "blue"):
        if channel in color:
            rgb[channel] = float(color[channel])
    if rgb:
        return {"color": {"rgbColor": rgb}}
    raise ValueError(f"{label} must define rgbColor or red/green/blue values")


def _docs_range(start_index: Any, end_index: Any) -> dict[str, int]:
    if start_index is None or end_index is None:
        raise ValueError("start_index and end_index are required")
    return {"startIndex": int(start_index), "endIndex": int(end_index)}


def _slides_text_range(start_index: Any, end_index: Any) -> dict[str, Any]:
    if start_index is None and end_index is None:
        return {"type": "ALL"}
    if start_index is not None and end_index is not None:
        return {"type": "FIXED_RANGE", "startIndex": int(start_index), "endIndex": int(end_index)}
    if start_index is not None:
        return {"type": "FROM_START_INDEX", "startIndex": int(start_index)}
    return {"type": "TO_END_INDEX", "endIndex": int(end_index)}


def _grid_range(value: Any) -> dict[str, Any]:
    raw = _as_dict(value, "grid_range")
    mapping = {
        "sheetId": "sheetId",
        "sheet_id": "sheetId",
        "startRowIndex": "startRowIndex",
        "start_row_index": "startRowIndex",
        "endRowIndex": "endRowIndex",
        "end_row_index": "endRowIndex",
        "startColumnIndex": "startColumnIndex",
        "start_column_index": "startColumnIndex",
        "endColumnIndex": "endColumnIndex",
        "end_column_index": "endColumnIndex",
    }
    out: dict[str, Any] = {}
    for source, target in mapping.items():
        if source in raw and raw[source] is not None:
            out[target] = int(raw[source])
    if "sheetId" not in out:
        raise ValueError("grid_range.sheetId is required")
    return out


def _build_calendar_event_body(args: dict[str, Any], recurring: bool = False) -> dict[str, Any]:
    start_time = str(args["start_time"])
    end_time = str(args["end_time"])
    body: dict[str, Any] = {
        "summary": args["summary"],
        "start": {"dateTime": start_time} if "T" in start_time else {"date": start_time},
        "end": {"dateTime": end_time} if "T" in end_time else {"date": end_time},
    }
    if args.get("description") is not None:
        body["description"] = args["description"]
    if args.get("location") is not None:
        body["location"] = args["location"]
    attendees = _normalize_attendees(args.get("attendees"))
    if attendees:
        body["attendees"] = attendees
    if args.get("timezone"):
        if body["start"].get("dateTime"):
            body["start"]["timeZone"] = args["timezone"]
        if body["end"].get("dateTime"):
            body["end"]["timeZone"] = args["timezone"]
    reminders = _parse_reminders(args.get("reminders"))
    if reminders or args.get("use_default_reminders") is False:
        body["reminders"] = {
            "useDefault": bool(args.get("use_default_reminders", True) and not reminders),
            "overrides": reminders or [],
        }
    if args.get("add_google_meet"):
        body["conferenceData"] = {
            "createRequest": {
                "requestId": secrets.token_hex(8),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
    if recurring:
        recurrence_lines = _as_string_list(args.get("recurrence"), "recurrence")
        if not recurrence_lines:
            raise ValueError("recurrence is required")
        recurrence_lines.extend(_as_string_list(args.get("exceptions"), "exceptions"))
        body["recurrence"] = recurrence_lines
    return body


class GoogleRuntime:
    def __init__(self, store: CredentialStore) -> None:
        self._store = store
        self._developer_key = _runtime_env("GOOGLE_API_KEY")
        self._default_user_email = _runtime_env("GOOGLE_DEFAULT_USER_EMAIL").lower()
        self._keep_master_token = GoogleKeepMasterTokenBackend(default_user_email=self._default_user_email)

    def _dispatch_keep_master_token(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return _dispatch_keep_master_token_impl(
            self,
            name,
            args,
            load_gkeepapi=_load_gkeepapi,
            as_list=_as_list,
            as_string_list=_as_string_list,
            json_export=_json_export,
            page_slice=_page_slice,
            keep_note_resource_name=_keep_note_resource_name,
        )

    def _svc(self, user_email: str | None, api: str, version: str):
        effective_user_email = str(user_email or self._default_user_email or "").strip().lower()
        creds = self._store.get(effective_user_email)
        if creds is not None:
            return build(api, version, credentials=creds, cache_discovery=False)

        if self._developer_key:
            return build(api, version, developerKey=self._developer_key, cache_discovery=False)
        raise PermissionError(
            "Google authorization required. Provide a stored OAuth credential for "
            "user_google_email or GOOGLE_DEFAULT_USER_EMAIL, or set GOOGLE_API_KEY "
            "for public-data-only requests."
        )

    def _resolve_drive_item(self, drive, file_id: str) -> tuple[str, dict[str, Any]]:
        return _resolve_drive_item_impl(drive, file_id)

    def _resolve_folder(self, drive, folder_id: str) -> str:
        return _resolve_folder_impl(drive, folder_id)

    async def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        user_email = args.get("user_google_email")
        if name in CALENDAR_TOOL_NAMES:
            return await _dispatch_calendar_impl(self, user_email, name, args, correct_time_format=_correct_time_format, build_calendar_event_body=_build_calendar_event_body, as_list=_as_list)
        if name in DOCS_TOOL_NAMES:
            return await _dispatch_docs_impl(self, user_email, name, args, json_export=_json_export, extract_doc_text=_extract_doc_text, docs_range=_docs_range, field_mask=_field_mask, optional_color=_optional_color)
        if name in DRIVE_TOOL_NAMES:
            return await _dispatch_drive_impl(self, user_email, name, args)
        if name in GMAIL_TOOL_NAMES:
            return await _dispatch_gmail_impl(self, user_email, name, args, extract_bodies=_extract_bodies, extract_headers=_extract_headers, as_dict=_as_dict)
        if name in SHEETS_TOOL_NAMES:
            return await _dispatch_sheets_impl(self, user_email, name, args, as_list=_as_list, as_string_list=_as_string_list, as_dict=_as_dict, grid_range=_grid_range)
        if name in SLIDES_TOOL_NAMES:
            return await _dispatch_slides_impl(self, user_email, name, args, json_export=_json_export, extract_slide_text=_extract_slide_text, slides_text_range=_slides_text_range, field_mask=_field_mask, optional_color=_optional_color)
        if name in TASKS_TOOL_NAMES:
            return await _dispatch_tasks_impl(self, user_email, name, args, normalize_due=_normalize_due)

        if name in MASTER_TOKEN_KEEP_TOOL_NAMES and self._keep_master_token.configured:
            return self._dispatch_keep_master_token(name, args)
        if name in CONTACTS_TOOL_NAMES:
            return await _dispatch_contacts_impl(self, user_email, name, args, as_string_list=_as_string_list, as_dict=_as_dict)
        if name in FORMS_TOOL_NAMES:
            return await _dispatch_forms_impl(self, user_email, name, args, as_list=_as_list, as_dict=_as_dict)
        if name in MEET_TOOL_NAMES:
            return await _dispatch_meet_impl(self, user_email, name, args)

        raise NotImplementedError(f"Tool '{name}' is not implemented")


def _register_tools(server: FastMCP, runtime: GoogleRuntime, manifest: list[dict[str, Any]]) -> None:
    _register_tools_impl(server, runtime.dispatch, manifest)


def _health_payload(
    credential_store: CredentialStore,
    keep_backend: GoogleKeepMasterTokenBackend,
) -> dict[str, Any]:
    auth_sources: list[str] = []
    if _runtime_env("GOOGLE_API_KEY"):
        auth_sources.append("google_api_key")
    if keep_backend.configured:
        auth_sources.append("google_keep_master_token")
    auth_sources.append("oauth_credentials_dir")

    return {
        "status": "ok",
        "server": "google-workspace-mcp",
        "credentialsDir": str(credential_store.base_dir),
        "mcpAuthMode": _runtime_env("API_KEY_MODE", default="static-or-disabled") or "static-or-disabled",
        "googleAuthSources": auth_sources,
        "googleApiKeyConfigured": bool(_runtime_env("GOOGLE_API_KEY")),
        "defaultUserEmail": _runtime_env("GOOGLE_DEFAULT_USER_EMAIL") or None,
        "keepMasterTokenConfigured": keep_backend.configured,
        "keepManagedLabel": keep_backend.managed_label_name if keep_backend.configured else None,
        "keepUnsafeMode": keep_backend.unsafe_mode,
        "legacyCredentialDecryption": bool(_runtime_env("MASTER_KEY")),
    }


manifest = _load_manifest()
credential_store = CredentialStore()
runtime = GoogleRuntime(credential_store)

api_keys = _load_api_keys()
auth = StaticApiKeyVerifier(api_keys=api_keys, base_url=_runtime_env("BASE_URL")) if api_keys else None
server = FastMCP("google-workspace-mcp", auth=auth)
mcp = server
_register_tools(server, runtime, manifest)


@server.custom_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root_health(_request):
    return JSONResponse(_health_payload(credential_store, runtime._keep_master_token))


@server.custom_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
async def health(_request):
    return JSONResponse(_health_payload(credential_store, runtime._keep_master_token))


@server.custom_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
async def healthz(_request):
    return JSONResponse(_health_payload(credential_store, runtime._keep_master_token))


def main() -> None:
    transport_name = _runtime_env("FASTMCP_TRANSPORT", default="streamable-http").lower()
    if transport_name == "http":
        transport_name = "streamable-http"
    if transport_name == "stdio":
        server.run()
    else:
        host = _runtime_env("HOST", default="127.0.0.1")
        port = int(_runtime_env("PORT", default="3002"))
        path = _runtime_env("MCP_PATH", default="/mcp")
        server.run(
            transport=transport_name,
            host=host,
            port=port,
            path=path,
            show_banner=False,
        )


if __name__ == "__main__":
    main()
