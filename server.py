
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.tools import FunctionTool
import gkeepapi
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
import requests
from starlette.responses import JSONResponse

RUNTIME_PLACEHOLDER_RE = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*\}$")
GOOGLE_API_SCOPES: dict[str, list[str]] = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "chat": [
        "https://www.googleapis.com/auth/chat.spaces",
        "https://www.googleapis.com/auth/chat.memberships",
        "https://www.googleapis.com/auth/chat.messages",
    ],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "forms": [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/drive",
    ],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.settings.basic",
    ],
    "keep": ["https://www.googleapis.com/auth/keep"],
    "meet": ["https://www.googleapis.com/auth/meetings.space.readonly"],
    "people": ["https://www.googleapis.com/auth/contacts"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "tasks": ["https://www.googleapis.com/auth/tasks"],
}
KEEP_MANAGED_LABEL_DEFAULT = "google-workspace-mcp"
KEEP_MANAGED_LABEL_LEGACY = "google-workspace-fast-mcp"
OFFICIAL_KEEP_TOOL_NAMES = {
    "list_keep_notes",
    "get_keep_note",
    "create_keep_note",
    "delete_keep_note",
    "download_keep_attachment",
    "share_keep_note",
    "unshare_keep_note",
    "get_keep_note_permissions",
}
ENHANCED_KEEP_TOOL_NAMES = {
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
MASTER_TOKEN_KEEP_TOOL_NAMES = OFFICIAL_KEEP_TOOL_NAMES | ENHANCED_KEEP_TOOL_NAMES


def _runtime_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        cleaned = value.strip()
        if not cleaned or RUNTIME_PLACEHOLDER_RE.fullmatch(cleaned):
            continue
        return cleaned
    return default


class StaticApiKeyVerifier(TokenVerifier):
    def __init__(self, api_keys: Iterable[str], base_url: str | None = None) -> None:
        super().__init__(base_url=base_url or None)
        self._api_keys = [key for key in api_keys if key]

    async def verify_token(self, token: str) -> AccessToken | None:
        for key in self._api_keys:
            if secrets.compare_digest(token, key):
                return AccessToken(token=token, client_id="google-workspace-mcp", scopes=[])
        return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _load_manifest() -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    manifest_paths = sorted(_repo_root().glob("tool_manifest_google*.json"))
    found = False
    for path in manifest_paths:
        if not path.exists():
            continue
        found = True
        data = json.loads(path.read_text(encoding="utf-8"))
        tools = data.get("tools")
        if not isinstance(tools, list):
            raise RuntimeError(f"{path.name} is invalid")
        for spec in tools:
            name = str((spec or {}).get("name") or "").strip()
            if name:
                merged[name] = spec
    if not found:
        raise FileNotFoundError(f"Missing tool manifest: {manifest_paths[0]}")
    return list(merged.values())


def _load_api_keys() -> list[str]:
    api_key_mode = _runtime_env("API_KEY_MODE", default="").strip().lower()
    if api_key_mode == "disabled":
        return []
    keys: list[str] = []
    for key in (_runtime_env("GOOGLE_WORKSPACE_MCP_API_KEY"), _runtime_env("MCP_API_KEY")):
        if key and key.strip():
            keys.append(key.strip())
    multi = _runtime_env("MCP_API_KEYS")
    if multi:
        keys.extend([x.strip() for x in multi.split(",") if x.strip()])
    return list(dict.fromkeys(keys))


def _derive_key(master_key: str) -> bytes:
    if re.fullmatch(r"[0-9a-fA-F]{64}", master_key or ""):
        return bytes.fromhex(master_key)
    return hashlib.sha256(master_key.encode("utf-8")).digest()


def _decrypt_legacy(master_key: str, encoded: str) -> dict[str, Any]:
    iv_hex, tag_hex, cipher_hex = str(encoded or "").split(":", 2)
    iv = bytes.fromhex(iv_hex)
    tag = bytes.fromhex(tag_hex)
    ciphertext = bytes.fromhex(cipher_hex)
    plaintext = AESGCM(_derive_key(master_key)).decrypt(iv, ciphertext + tag, None)
    return json.loads(plaintext.decode("utf-8"))


def _parse_expiry(payload: dict[str, Any]) -> datetime | None:
    value = payload.get("expiry_date")
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(tzinfo=None)
        return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
    value = payload.get("expiry")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _as_scopes(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        value = value.strip()
        return value.split() if value else None
    return None


class CredentialStore:
    def __init__(self) -> None:
        custom_dir = _runtime_env("GOOGLE_MCP_CREDENTIALS_DIR")
        self._base_dir = Path(custom_dir).expanduser() if custom_dir else Path.home() / ".google_workspace_mcp" / "credentials"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def _path(self, email: str) -> Path:
        return self._base_dir / f"{email}.json"

    def get(self, email: str) -> Credentials | None:
        user = str(email or "").strip().lower()
        if not user:
            return None
        path = self._path(user)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            master_key = _runtime_env("MASTER_KEY")
            if not master_key:
                return None
            try:
                payload = _decrypt_legacy(master_key, raw)
            except Exception:
                return None

        client_id = payload.get("oauth_client_id") or _runtime_env("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = payload.get("oauth_client_secret") or _runtime_env("GOOGLE_OAUTH_CLIENT_SECRET")
        token = payload.get("token") or payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        token_uri = payload.get("token_uri") or "https://oauth2.googleapis.com/token"
        scopes = _as_scopes(payload.get("scopes") or payload.get("scope"))
        if not client_id or not client_secret or (not token and not refresh_token):
            return None

        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        expiry = _parse_expiry(payload)
        if expiry is not None:
            creds.expiry = expiry
        if not creds.valid and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
            except Exception:
                return None
        return creds


class ServiceAccountStore:
    def __init__(self) -> None:
        self._json = _runtime_env("GOOGLE_SERVICE_ACCOUNT_JSON")
        self._file = _runtime_env("GOOGLE_SERVICE_ACCOUNT_FILE")
        self._default_subject = _runtime_env("GOOGLE_IMPERSONATED_USER")

    @property
    def configured(self) -> bool:
        return bool(self._json or self._file)

    @property
    def default_subject(self) -> str:
        return self._default_subject

    def get(self, scopes: list[str], subject: str | None = None) -> ServiceAccountCredentials | None:
        if not self.configured:
            return None

        try:
            if self._json:
                info = json.loads(self._json)
                creds = ServiceAccountCredentials.from_service_account_info(info, scopes=scopes)
            else:
                creds = ServiceAccountCredentials.from_service_account_file(self._file, scopes=scopes)
        except Exception:
            return None

        effective_subject = str(subject or self._default_subject or "").strip()
        if effective_subject:
            creds = creds.with_subject(effective_subject)
        return creds


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
    def __init__(self, store: CredentialStore, service_accounts: ServiceAccountStore) -> None:
        self._store = store
        self._service_accounts = service_accounts
        self._developer_key = _runtime_env("GOOGLE_API_KEY")
        self._default_user_email = _runtime_env("GOOGLE_DEFAULT_USER_EMAIL").lower()
        self._keep_master_token = GoogleKeepMasterTokenBackend(default_user_email=self._default_user_email)

    def _dispatch_keep_master_token(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        keep_backend = self._keep_master_token
        user_email = args.get("user_google_email")
        if not keep_backend.configured:
            raise PermissionError(
                "Enhanced Google Keep tools require GOOGLE_KEEP_MASTER_TOKEN and "
                "GOOGLE_KEEP_EMAIL or GOOGLE_DEFAULT_USER_EMAIL."
            )

        if name in {"list_keep_notes", "find_keep_notes"}:
            keep = keep_backend.client(user_email)
            query = str(args.get("query") or args.get("filter") or "").strip()
            notes = list(
                keep.find(
                    query=query,
                    labels=keep_backend.resolve_labels(keep, args.get("labels")),
                    colors=keep_backend.normalize_colors(args.get("colors")),
                    pinned=args.get("pinned"),
                    archived=args.get("archived", False),
                    trashed=args.get("trashed", False),
                )
            )
            page, next_token = _page_slice(notes, args.get("page_size", 25), args.get("page_token"))
            return {
                "notes": [keep_backend.serialize_note(note) for note in page],
                "nextPageToken": next_token,
                "estimatedTotal": len(notes),
            }

        if name == "get_keep_note":
            _keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            return {"note": keep_backend.serialize_note(note)}

        if name == "create_keep_note":
            keep = keep_backend.client(user_email)
            list_items = _as_list(args.get("list_items"), "list_items") if isinstance(args.get("list_items"), str) else args.get("list_items")
            if args.get("text") and list_items:
                raise ValueError("Provide either text or list_items, not both")
            if list_items:
                formatted = [
                    (str((item or {}).get("text") or ""), bool((item or {}).get("checked", False)))
                    for item in list_items
                ]
                note = keep.createList(title=args.get("title"), items=formatted)
            else:
                note = keep.createNote(title=args.get("title"), text=args.get("text"))
            managed_label = keep_backend.ensure_managed_label(keep)
            if managed_label is not None:
                note.labels.add(managed_label)
            keep.sync()
            return {"created": True, "note": keep_backend.serialize_note(note)}

        if name == "create_keep_list":
            keep = keep_backend.client(user_email)
            items = _as_list(args.get("items"), "items") if isinstance(args.get("items"), str) else args.get("items")
            formatted_items = [
                (str((item or {}).get("text") or ""), bool((item or {}).get("checked", False)))
                for item in (items or [])
            ]
            note = keep.createList(title=args.get("title"), items=formatted_items or None)
            managed_label = keep_backend.ensure_managed_label(keep)
            if managed_label is not None:
                note.labels.add(managed_label)
            keep.sync()
            return {"created": True, "note": keep_backend.serialize_note(note)}

        if name == "update_keep_note":
            keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            keep_backend.ensure_modifiable(note)
            if args.get("title") is not None:
                note.title = str(args.get("title") or "")
            if args.get("text") is not None:
                note.text = str(args.get("text") or "")
            keep.sync()
            return {"updated": True, "note": keep_backend.serialize_note(note)}

        if name in {"add_keep_list_item", "update_keep_list_item", "delete_keep_list_item"}:
            keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            keep_backend.ensure_modifiable(note)
            if not isinstance(note, gkeepapi.node.List):
                raise ValueError(f"Note {note.id} is not a checklist")
            if name == "add_keep_list_item":
                item = note.add(text=args["text"], checked=bool(args.get("checked", False)))
                keep.sync()
                return {"created": True, "item": keep_backend.serialize_list_item(item), "note": keep_backend.serialize_note(note)}
            item = note.get(args["item_id"])
            if item is None:
                raise ValueError(f"List item '{args['item_id']}' was not found")
            if name == "update_keep_list_item":
                if args.get("text") is not None:
                    item.text = str(args.get("text") or "")
                if args.get("checked") is not None:
                    item.checked = bool(args.get("checked"))
                keep.sync()
                return {"updated": True, "note": keep_backend.serialize_note(note)}
            item.delete()
            keep.sync()
            return {"deleted": True, "itemId": args["item_id"], "note": keep_backend.serialize_note(note)}

        if name == "set_keep_note_color":
            keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            keep_backend.ensure_modifiable(note)
            try:
                note.color = gkeepapi.node.ColorValue(str(args["color"]).upper())
            except ValueError as exc:
                raise ValueError(f"Invalid Keep color '{args['color']}'") from exc
            keep.sync()
            return {"updated": True, "note": keep_backend.serialize_note(note)}

        if name in {"pin_keep_note", "archive_keep_note", "trash_keep_note", "restore_keep_note", "delete_keep_note"}:
            keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            keep_backend.ensure_modifiable(note)
            if name == "pin_keep_note":
                note.pinned = bool(args.get("pinned", True))
            elif name == "archive_keep_note":
                note.archived = bool(args.get("archived", True))
            elif name == "trash_keep_note":
                note.trash()
            elif name == "restore_keep_note":
                note.untrash()
                note.undelete()
            else:
                note.delete()
            keep.sync()
            return {"updated": True, "note": keep_backend.serialize_note(note)}

        if name in {"list_keep_labels", "create_keep_label", "delete_keep_label"}:
            keep = keep_backend.client(user_email)
            if name == "list_keep_labels":
                return {"labels": [keep_backend.serialize_label(label) for label in keep.labels()]}
            if name == "create_keep_label":
                label = keep.createLabel(args["name"])
                keep.sync()
                return {"created": True, "label": keep_backend.serialize_label(label)}
            label = keep_backend.resolve_label(keep, args["label_id"])
            if label.name == keep_backend.managed_label_name and not keep_backend.unsafe_mode:
                raise ValueError(
                    f"Cannot delete the managed label '{keep_backend.managed_label_name}' "
                    "unless GOOGLE_KEEP_UNSAFE_MODE=true."
                )
            keep.deleteLabel(label.id)
            keep.sync()
            return {"deleted": True, "labelId": label.id}

        if name in {"add_keep_label_to_note", "remove_keep_label_from_note"}:
            keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            keep_backend.ensure_modifiable(note)
            label = keep_backend.resolve_label(keep, args["label_id"])
            if name == "remove_keep_label_from_note" and label.name == keep_backend.managed_label_name and not keep_backend.unsafe_mode:
                raise ValueError(
                    f"Cannot remove the managed label '{keep_backend.managed_label_name}' "
                    "unless GOOGLE_KEEP_UNSAFE_MODE=true."
                )
            if name == "add_keep_label_to_note":
                note.labels.add(label)
            else:
                note.labels.remove(label)
            keep.sync()
            return {"updated": True, "note": keep_backend.serialize_note(note)}

        if name in {"list_keep_note_collaborators", "share_keep_note", "add_keep_note_collaborator", "unshare_keep_note", "remove_keep_note_collaborator", "get_keep_note_permissions"}:
            keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
            if name in {"share_keep_note", "add_keep_note_collaborator", "unshare_keep_note", "remove_keep_note_collaborator"}:
                keep_backend.ensure_modifiable(note)
            if name == "list_keep_note_collaborators":
                return {"collaborators": list(note.collaborators.all())}
            if name == "get_keep_note_permissions":
                return {
                    "permissions": [
                        {"email": email, "role": "WRITER"} for email in note.collaborators.all()
                    ]
                }
            if name == "share_keep_note":
                emails = _as_string_list(args.get("writers"), "writers")
            elif name == "add_keep_note_collaborator":
                emails = [str(args["email"]).strip()]
            elif name == "unshare_keep_note":
                emails = _as_string_list(args.get("emails_or_groups"), "emails_or_groups")
            else:
                emails = [str(args["email"]).strip()]
            for email in emails:
                if name in {"share_keep_note", "add_keep_note_collaborator"}:
                    note.collaborators.add(email)
                else:
                    note.collaborators.remove(email)
            keep.sync()
            return {"updated": True, "note": keep_backend.serialize_note(note)}

        if name == "list_keep_note_media":
            return {"media": keep_backend.list_media(user_email, args["note_name"])}

        if name == "download_keep_attachment":
            note, blob, detected_mime_type = keep_backend.find_blob(user_email, args["attachment_name"])
            media_link = keep_backend.client(user_email).getMediaLink(blob)
            response = requests.get(media_link, timeout=30)
            response.raise_for_status()
            mime_type = str(args.get("mime_type") or response.headers.get("Content-Type") or detected_mime_type or "application/octet-stream")
            return {
                "attachmentName": args["attachment_name"],
                "noteName": _keep_note_resource_name(note.id),
                "mediaLink": media_link,
                **_json_export(response.content, mime_type),
            }

        raise NotImplementedError(f"Tool '{name}' is not implemented for Google Keep master-token auth")

    def _svc(self, user_email: str | None, api: str, version: str):
        effective_user_email = str(user_email or self._default_user_email or "").strip().lower()
        creds = self._store.get(effective_user_email)
        if creds is not None:
            return build(api, version, credentials=creds, cache_discovery=False)

        creds = self._service_accounts.get(GOOGLE_API_SCOPES.get(api, []), subject=effective_user_email or None)
        if creds is None:
            if self._developer_key:
                return build(api, version, developerKey=self._developer_key, cache_discovery=False)
            raise PermissionError(
                "Google authorization required. Configure GOOGLE_SERVICE_ACCOUNT_FILE or "
                "GOOGLE_SERVICE_ACCOUNT_JSON for non-interactive Workspace access, provide a stored "
                "OAuth credential for user_google_email or GOOGLE_DEFAULT_USER_EMAIL, or set "
                "GOOGLE_API_KEY for public-data-only requests."
            )
        return build(api, version, credentials=creds, cache_discovery=False)

    def _resolve_drive_item(self, drive, file_id: str) -> tuple[str, dict[str, Any]]:
        current = file_id
        for _ in range(6):
            meta = drive.files().get(
                fileId=current,
                fields="id,mimeType,shortcutDetails(targetId,targetMimeType),name,webViewLink",
                supportsAllDrives=True,
            ).execute()
            if meta.get("mimeType") != "application/vnd.google-apps.shortcut":
                return current, meta
            target = ((meta.get("shortcutDetails") or {}).get("targetId"))
            if not target:
                break
            current = target
        raise RuntimeError(f"Unable to resolve drive item: {file_id}")

    def _resolve_folder(self, drive, folder_id: str) -> str:
        resolved, meta = self._resolve_drive_item(drive, folder_id)
        if meta.get("mimeType") != "application/vnd.google-apps.folder":
            raise RuntimeError(f"Resolved id '{resolved}' is not a folder")
        return resolved

    async def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        user_email = args.get("user_google_email")
        if name in {
            "list_calendars",
            "get_events",
            "create_event",
            "delete_event",
            "get_free_busy",
            "list_calendar_acl",
            "create_calendar_acl_rule",
            "delete_calendar_acl_rule",
            "create_recurring_event",
        }:
            svc = self._svc(user_email, "calendar", "v3")
            if name == "list_calendars":
                data = svc.calendarList().list(maxResults=args.get("page_size", 100), pageToken=args.get("page_token")).execute()
                return {"calendars": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
            if name == "get_events":
                calendar_id = args.get("calendar_id", "primary")
                if args.get("event_id"):
                    return {"event": svc.events().get(calendarId=calendar_id, eventId=args["event_id"]).execute()}
                params: dict[str, Any] = {
                    "calendarId": calendar_id,
                    "maxResults": args.get("page_size", 25),
                    "singleEvents": True,
                    "orderBy": "startTime",
                    "pageToken": args.get("page_token"),
                    "q": args.get("query"),
                    "timeMin": _correct_time_format(args.get("time_min")) or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
                if args.get("time_max"):
                    params["timeMax"] = _correct_time_format(args["time_max"])
                data = svc.events().list(**params).execute()
                return {"events": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
            if name in {"create_event", "create_recurring_event"}:
                body = _build_calendar_event_body(args, recurring=name == "create_recurring_event")
                params: dict[str, Any] = {
                    "calendarId": args.get("calendar_id", "primary"),
                    "body": body,
                    "conferenceDataVersion": 1 if args.get("add_google_meet") else 0,
                }
                if args.get("send_updates"):
                    params["sendUpdates"] = args["send_updates"]
                if args.get("supports_attachments") is not None:
                    params["supportsAttachments"] = bool(args["supports_attachments"])
                data = svc.events().insert(**params).execute()
                return {"created": True, "event": data}
            if name == "delete_event":
                svc.events().delete(calendarId=args.get("calendar_id", "primary"), eventId=args["event_id"]).execute()
                return {"deleted": True, "eventId": args["event_id"]}
            if name == "get_free_busy":
                items = [{"id": item} if isinstance(item, str) else item for item in (_as_list(args.get("items"), "items") if isinstance(args.get("items"), str) else args.get("items") or [])]
                if not items:
                    raise ValueError("items is required")
                body = {"timeMin": _correct_time_format(args["time_min"]), "timeMax": _correct_time_format(args["time_max"]), "items": items}
                if args.get("time_zone"):
                    body["timeZone"] = args["time_zone"]
                return {"freeBusy": svc.freebusy().query(body=body).execute()}
            if name == "list_calendar_acl":
                data = svc.acl().list(
                    calendarId=args.get("calendar_id", "primary"),
                    maxResults=args.get("page_size", 100),
                    pageToken=args.get("page_token"),
                    showDeleted=args.get("show_deleted", False),
                ).execute()
                return {"rules": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
            if name == "create_calendar_acl_rule":
                body = {
                    "role": args["role"],
                    "scope": {"type": args["scope_type"], "value": args["scope_value"]},
                }
                data = svc.acl().insert(
                    calendarId=args.get("calendar_id", "primary"),
                    body=body,
                    sendNotifications=args.get("send_notifications", False),
                ).execute()
                return {"created": True, "rule": data}
            if name == "delete_calendar_acl_rule":
                svc.acl().delete(calendarId=args.get("calendar_id", "primary"), ruleId=args["rule_id"]).execute()
                return {"deleted": True, "ruleId": args["rule_id"]}

        if name in {"list_spaces", "create_space", "list_members", "add_member", "remove_member", "get_messages", "send_message", "reply_in_thread"}:
            svc = self._svc(user_email, "chat", "v1")
            if name == "list_spaces":
                flt = ""
                if args.get("space_type") == "room":
                    flt = 'spaceType = "SPACE"'
                elif args.get("space_type") == "dm":
                    flt = 'spaceType = "DIRECT_MESSAGE"'
                return {"spaces": svc.spaces().list(pageSize=args.get("page_size", 100), filter=flt).execute().get("spaces", [])}
            if name == "create_space":
                data = svc.spaces().create(body={"displayName": args["display_name"], "spaceType": args.get("space_type", "SPACE"), "externalUserAllowed": args.get("external_user_allowed", False)}).execute()
                return {"created": True, "space": data}
            if name == "list_members":
                data = svc.spaces().members().list(parent=args["space_id"], pageSize=args.get("page_size", 100)).execute()
                return {"memberships": data.get("memberships", [])}
            if name == "add_member":
                data = svc.spaces().members().create(parent=args["space_id"], body={"member": {"name": args["member_name"]}}).execute()
                return {"created": True, "membership": data}
            if name == "remove_member":
                svc.spaces().members().delete(name=args["member_name"]).execute()
                return {"deleted": True, "memberName": args["member_name"]}
            if name == "get_messages":
                data = svc.spaces().messages().list(parent=args["space_id"], pageSize=args.get("page_size", 50), orderBy="createTime desc").execute()
                return {"messages": data.get("messages", [])}
            params: dict[str, Any] = {"parent": args["space_id"], "body": {"text": args["message_text"]}}
            if name == "reply_in_thread":
                thread_name = str(args.get("thread_name") or "").strip()
                thread_key = str(args.get("thread_key") or "").strip()
                if not thread_name and not thread_key:
                    raise ValueError("thread_name or thread_key is required")
                if thread_name:
                    params["body"]["thread"] = {"name": thread_name}
                if thread_key:
                    params["threadKey"] = thread_key
                params["messageReplyOption"] = args.get("message_reply_option", "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD")
            elif args.get("thread_key"):
                params["threadKey"] = args["thread_key"]
            return {"sent": True, "message": svc.spaces().messages().create(**params).execute()}

        if name in {"create_doc", "get_doc_content", "modify_doc_text", "apply_doc_paragraph_style", "apply_doc_text_style", "export_doc"}:
            if name == "export_doc":
                drive = self._svc(user_email, "drive", "v3")
                export_formats = {
                    "pdf": "application/pdf",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "html": "text/html",
                }
                export_format = str(args.get("format", "pdf")).lower()
                if export_format not in export_formats:
                    raise ValueError("format must be one of: pdf, docx, html")
                raw = drive.files().export(fileId=args["document_id"], mimeType=export_formats[export_format]).execute()
                return {"documentId": args["document_id"], **_json_export(raw, export_formats[export_format])}
            svc = self._svc(user_email, "docs", "v1")
            if name == "create_doc":
                data = svc.documents().create(body={"title": args["title"]}).execute()
                if args.get("content") and data.get("documentId"):
                    svc.documents().batchUpdate(documentId=data["documentId"], body={"requests": [{"insertText": {"location": {"index": 1}, "text": args["content"]}}]}).execute()
                return {"created": True, "document": data}
            if name == "get_doc_content":
                data = svc.documents().get(documentId=args["document_id"]).execute()
                return {"document": data, "text": _extract_doc_text((data.get("body") or {}).get("content"))}
            if name == "modify_doc_text":
                reqs: list[dict[str, Any]] = []
                if args.get("start_index") is not None and args.get("end_index") is not None:
                    reqs.append({"deleteContentRange": {"range": {"startIndex": int(args["start_index"]), "endIndex": int(args["end_index"])}}})
                    reqs.append({"insertText": {"location": {"index": int(args["start_index"])}, "text": args["text"]}})
                else:
                    reqs.append({"insertText": {"location": {"index": int(args.get("index", 1))}, "text": args["text"]}})
                data = svc.documents().batchUpdate(documentId=args["document_id"], body={"requests": reqs}).execute()
                return {"updated": True, "result": data}
            if name == "apply_doc_paragraph_style":
                style: dict[str, Any] = {}
                fields: list[str] = []
                if args.get("named_style_type"):
                    style["namedStyleType"] = args["named_style_type"]
                    fields.append("namedStyleType")
                if args.get("alignment"):
                    style["alignment"] = args["alignment"]
                    fields.append("alignment")
                if not fields:
                    raise ValueError("At least one paragraph style field is required")
                data = svc.documents().batchUpdate(
                    documentId=args["document_id"],
                    body={
                        "requests": [{
                            "updateParagraphStyle": {
                                "range": _docs_range(args.get("start_index"), args.get("end_index")),
                                "paragraphStyle": style,
                                "fields": _field_mask(*fields),
                            }
                        }]
                    },
                ).execute()
                return {"updated": True, "result": data}
            style = {}
            fields = []
            for key in ("bold", "italic", "underline", "strikethrough"):
                if args.get(key) is not None:
                    style[key] = bool(args[key])
                    fields.append(key)
            if args.get("link_url"):
                style["link"] = {"url": args["link_url"]}
                fields.append("link")
            if args.get("font_size_pt") is not None:
                style["fontSize"] = {"magnitude": float(args["font_size_pt"]), "unit": "PT"}
                fields.append("fontSize")
            if args.get("weighted_font_family"):
                style["weightedFontFamily"] = {"fontFamily": args["weighted_font_family"]}
                fields.append("weightedFontFamily")
            color = _optional_color(args.get("foreground_color"), "foreground_color")
            if color:
                style["foregroundColor"] = color
                fields.append("foregroundColor")
            if not fields:
                raise ValueError("At least one text style field is required")
            data = svc.documents().batchUpdate(
                documentId=args["document_id"],
                body={
                    "requests": [{
                        "updateTextStyle": {
                            "range": _docs_range(args.get("start_index"), args.get("end_index")),
                            "textStyle": style,
                            "fields": _field_mask(*fields),
                        }
                    }]
                },
            ).execute()
            return {"updated": True, "result": data}
        if name in {
            "search_drive_files",
            "list_drive_items",
            "get_drive_file_content",
            "create_drive_file",
            "get_drive_file_permissions",
            "create_drive_folder",
            "copy_drive_file",
            "trash_drive_file",
            "untrash_drive_file",
            "delete_drive_file",
            "list_drive_revisions",
            "get_drive_revision",
            "list_shared_drives",
        }:
            svc = self._svc(user_email, "drive", "v3")
            if name == "search_drive_files":
                query = str(args["query"])
                if "=" not in query and "contains" not in query:
                    escaped = query.replace("'", "\\'")
                    query = f"fullText contains '{escaped}'"
                params: dict[str, Any] = {
                    "q": query,
                    "pageSize": args.get("page_size", 10),
                    "pageToken": args.get("page_token"),
                    "fields": "nextPageToken, files(id,name,mimeType,webViewLink,iconLink,modifiedTime,size)",
                    "supportsAllDrives": True,
                    "includeItemsFromAllDrives": args.get("include_items_from_all_drives", True),
                }
                if args.get("drive_id"):
                    params["driveId"] = args["drive_id"]
                    params["corpora"] = args.get("corpora", "drive")
                elif args.get("corpora"):
                    params["corpora"] = args["corpora"]
                data = svc.files().list(**params).execute()
                return {"files": data.get("files", []), "nextPageToken": data.get("nextPageToken")}
            if name == "list_drive_items":
                folder_id = self._resolve_folder(svc, args.get("folder_id", "root"))
                params: dict[str, Any] = {
                    "q": f"'{folder_id}' in parents and trashed=false",
                    "pageSize": args.get("page_size", 100),
                    "pageToken": args.get("page_token"),
                    "fields": "nextPageToken, files(id,name,mimeType,webViewLink,iconLink,modifiedTime,size)",
                    "supportsAllDrives": True,
                    "includeItemsFromAllDrives": args.get("include_items_from_all_drives", True),
                }
                if args.get("drive_id"):
                    params["driveId"] = args["drive_id"]
                    params["corpora"] = args.get("corpora", "drive")
                elif args.get("corpora"):
                    params["corpora"] = args["corpora"]
                data = svc.files().list(**params).execute()
                return {"files": data.get("files", []), "nextPageToken": data.get("nextPageToken")}
            if name == "get_drive_file_content":
                file_id, meta = self._resolve_drive_item(svc, args["file_id"])
                mime_type = meta.get("mimeType")
                if mime_type == "application/vnd.google-apps.document":
                    raw = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
                    content = raw.decode("utf-8", errors="replace")
                elif mime_type == "application/vnd.google-apps.spreadsheet":
                    raw = svc.files().export(fileId=file_id, mimeType="text/csv").execute()
                    content = raw.decode("utf-8", errors="replace")
                else:
                    raw = svc.files().get(fileId=file_id, alt="media").execute()
                    content = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                return {"file": meta, "resolvedId": file_id, "content": content}
            if name == "create_drive_file":
                if not args.get("content"):
                    raise ValueError("content is required")
                folder_id = self._resolve_folder(svc, args.get("folder_id", "root"))
                data = svc.files().create(body={"name": args["file_name"], "parents": [folder_id], "mimeType": args.get("mime_type", "text/plain")}, media_body=args["content"], fields="id,name,webViewLink,mimeType", supportsAllDrives=True).execute()
                return {"created": True, "file": data}
            if name == "get_drive_file_permissions":
                file_id, _ = self._resolve_drive_item(svc, args["file_id"])
                data = svc.files().get(fileId=file_id, fields="id,name,mimeType,size,modifiedTime,permissions(id,type,role,emailAddress,domain,expirationTime),webViewLink,shared", supportsAllDrives=True).execute()
                return {"file": data}
            if name == "create_drive_folder":
                parent_id = self._resolve_folder(svc, args.get("parent_folder_id", "root"))
                data = svc.files().create(
                    body={
                        "name": args["folder_name"],
                        "parents": [parent_id],
                        "mimeType": "application/vnd.google-apps.folder",
                    },
                    fields="id,name,webViewLink,mimeType,parents",
                    supportsAllDrives=True,
                ).execute()
                return {"created": True, "folder": data}
            if name == "copy_drive_file":
                file_id, _ = self._resolve_drive_item(svc, args["file_id"])
                body: dict[str, Any] = {}
                if args.get("name"):
                    body["name"] = args["name"]
                if args.get("parent_folder_id"):
                    body["parents"] = [self._resolve_folder(svc, args["parent_folder_id"])]
                data = svc.files().copy(
                    fileId=file_id,
                    body=body,
                    fields="id,name,webViewLink,mimeType,parents",
                    supportsAllDrives=True,
                ).execute()
                return {"copied": True, "file": data}
            if name in {"trash_drive_file", "untrash_drive_file"}:
                file_id, _ = self._resolve_drive_item(svc, args["file_id"])
                data = svc.files().update(
                    fileId=file_id,
                    body={"trashed": name == "trash_drive_file"},
                    fields="id,name,trashed,webViewLink",
                    supportsAllDrives=True,
                ).execute()
                return {"updated": True, "trashed": data.get("trashed"), "file": data}
            if name == "delete_drive_file":
                file_id, _ = self._resolve_drive_item(svc, args["file_id"])
                svc.files().delete(fileId=file_id, supportsAllDrives=True).execute()
                return {"deleted": True, "fileId": file_id}
            if name == "list_drive_revisions":
                file_id, _ = self._resolve_drive_item(svc, args["file_id"])
                data = svc.revisions().list(
                    fileId=file_id,
                    pageSize=args.get("page_size", 50),
                    pageToken=args.get("page_token"),
                    fields="nextPageToken,revisions(id,mimeType,modifiedTime,keepForever,size,published,lastModifyingUser(displayName,emailAddress))",
                ).execute()
                return {"revisions": data.get("revisions", []), "nextPageToken": data.get("nextPageToken")}
            if name == "get_drive_revision":
                file_id, _ = self._resolve_drive_item(svc, args["file_id"])
                data = svc.revisions().get(
                    fileId=file_id,
                    revisionId=args["revision_id"],
                    fields="id,mimeType,modifiedTime,keepForever,size,published,lastModifyingUser(displayName,emailAddress),exportLinks",
                ).execute()
                return {"revision": data}
            if name == "list_shared_drives":
                data = svc.drives().list(pageSize=args.get("page_size", 100), pageToken=args.get("page_token")).execute()
                return {"sharedDrives": data.get("drives", []), "nextPageToken": data.get("nextPageToken")}

        if name in {
            "search_gmail_messages",
            "get_gmail_message_content",
            "get_gmail_messages_content_batch",
            "get_gmail_attachment_content",
            "archive_gmail_message",
            "trash_gmail_message",
            "mark_gmail_read_unread",
            "star_unstar_gmail_message",
            "list_gmail_filters",
            "create_gmail_filter",
            "delete_gmail_filter",
        }:
            svc = self._svc(user_email, "gmail", "v1")
            if name == "search_gmail_messages":
                data = svc.users().messages().list(userId="me", q=args["query"], maxResults=args.get("page_size", 10), pageToken=args.get("page_token")).execute()
                return {"messages": data.get("messages", []), "nextPageToken": data.get("nextPageToken")}
            if name == "get_gmail_message_content":
                msg = svc.users().messages().get(userId="me", id=args["message_id"], format="full").execute()
                payload = msg.get("payload") or {}
                text_body, html_body = _extract_bodies(payload)
                return {"message": msg, "headers": _extract_headers(payload.get("headers"), ["Subject", "From", "To", "Cc", "Message-ID", "Date"]), "body": text_body or html_body, "textBody": text_body, "htmlBody": html_body}
            if name == "get_gmail_messages_content_batch":
                fmt = args.get("format", "full")
                out: list[dict[str, Any]] = []
                for message_id in (args.get("message_ids") or [])[:25]:
                    try:
                        msg = svc.users().messages().get(userId="me", id=message_id, format="metadata" if fmt == "metadata" else "full", metadataHeaders=["Subject", "From", "To", "Cc", "Message-ID", "Date"]).execute()
                        payload = msg.get("payload") or {}
                        item: dict[str, Any] = {"messageId": message_id, "headers": _extract_headers(payload.get("headers"), ["Subject", "From", "Date"]), "message": msg}
                        if fmt != "metadata":
                            text_body, html_body = _extract_bodies(payload)
                            item["body"] = text_body or html_body
                        out.append(item)
                    except Exception as exc:
                        out.append({"messageId": message_id, "error": str(exc)})
                return {"results": out}
            if name == "get_gmail_attachment_content":
                data = svc.users().messages().attachments().get(userId="me", messageId=args["message_id"], id=args["attachment_id"]).execute()
                return {"attachment": data}
            if name == "archive_gmail_message":
                data = svc.users().messages().modify(userId="me", id=args["message_id"], body={"removeLabelIds": ["INBOX"]}).execute()
                return {"archived": True, "message": data}
            if name == "trash_gmail_message":
                data = svc.users().messages().trash(userId="me", id=args["message_id"]).execute()
                return {"trashed": True, "message": data}
            if name == "mark_gmail_read_unread":
                mark_read = bool(args.get("mark_read", True))
                body = {"removeLabelIds": ["UNREAD"]} if mark_read else {"addLabelIds": ["UNREAD"]}
                data = svc.users().messages().modify(userId="me", id=args["message_id"], body=body).execute()
                return {"updated": True, "markRead": mark_read, "message": data}
            if name == "star_unstar_gmail_message":
                starred = bool(args.get("starred", True))
                body = {"addLabelIds": ["STARRED"]} if starred else {"removeLabelIds": ["STARRED"]}
                data = svc.users().messages().modify(userId="me", id=args["message_id"], body=body).execute()
                return {"updated": True, "starred": starred, "message": data}
            if name == "list_gmail_filters":
                data = svc.users().settings().filters().list(userId="me").execute()
                return {"filters": data.get("filter", [])}
            if name == "create_gmail_filter":
                criteria = _as_dict(args.get("criteria"), "criteria")
                action = _as_dict(args.get("action"), "action")
                if not criteria or not action:
                    raise ValueError("criteria and action are required")
                data = svc.users().settings().filters().create(userId="me", body={"criteria": criteria, "action": action}).execute()
                return {"created": True, "filter": data}
            if name == "delete_gmail_filter":
                svc.users().settings().filters().delete(userId="me", id=args["filter_id"]).execute()
                return {"deleted": True, "filterId": args["filter_id"]}

        if name in {
            "list_spreadsheets",
            "get_spreadsheet_info",
            "read_sheet_values",
            "modify_sheet_values",
            "append_sheet_rows",
            "batch_get_sheet_values",
            "batch_update_sheet_values",
            "create_named_range",
            "update_named_range",
            "delete_named_range",
            "add_data_validation",
            "set_protected_range",
            "create_chart",
            "update_chart",
            "create_pivot_table",
            "format_sheet_range",
            "add_conditional_formatting",
            "update_conditional_formatting",
            "delete_conditional_formatting",
        }:
            if name == "list_spreadsheets":
                svc = self._svc(user_email, "drive", "v3")
                data = svc.files().list(q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false", pageSize=args.get("page_size", 25), pageToken=args.get("page_token"), fields="nextPageToken, files(id,name,modifiedTime,webViewLink)", orderBy="modifiedTime desc", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                return {"spreadsheets": data.get("files", []), "nextPageToken": data.get("nextPageToken")}
            svc = self._svc(user_email, "sheets", "v4")
            if name == "get_spreadsheet_info":
                data = svc.spreadsheets().get(spreadsheetId=args["spreadsheet_id"], fields="spreadsheetId,properties(title,locale),sheets(properties(title,sheetId,gridProperties(rowCount,columnCount)))").execute()
                return {"spreadsheet": data}
            if name == "read_sheet_values":
                data = svc.spreadsheets().values().get(spreadsheetId=args["spreadsheet_id"], range=args.get("range_name", "A1:Z1000")).execute()
                return {"range": data.get("range"), "values": data.get("values", [])}
            if name == "modify_sheet_values":
                if args.get("clear_values"):
                    data = svc.spreadsheets().values().clear(spreadsheetId=args["spreadsheet_id"], range=args["range_name"], body={}).execute()
                    return {"cleared": True, "result": data}
                values = args.get("values")
                if isinstance(values, str):
                    values = json.loads(values)
                if not isinstance(values, list):
                    raise ValueError("values must be a 2D array")
                data = svc.spreadsheets().values().update(spreadsheetId=args["spreadsheet_id"], range=args["range_name"], valueInputOption=args.get("value_input_option", "USER_ENTERED"), body={"values": values}).execute()
                return {"updated": True, "result": data}
            if name == "append_sheet_rows":
                values = _as_list(args.get("values"), "values") if isinstance(args.get("values"), str) else args.get("values")
                if not isinstance(values, list):
                    raise ValueError("values must be a 2D array")
                data = svc.spreadsheets().values().append(
                    spreadsheetId=args["spreadsheet_id"],
                    range=args["range_name"],
                    valueInputOption=args.get("value_input_option", "USER_ENTERED"),
                    insertDataOption=args.get("insert_data_option", "INSERT_ROWS"),
                    body={"values": values},
                ).execute()
                return {"appended": True, "result": data}
            if name == "batch_get_sheet_values":
                ranges = _as_string_list(args.get("ranges"), "ranges")
                if not ranges:
                    raise ValueError("ranges is required")
                data = svc.spreadsheets().values().batchGet(
                    spreadsheetId=args["spreadsheet_id"],
                    ranges=ranges,
                    majorDimension=args.get("major_dimension"),
                ).execute()
                return {"valueRanges": data.get("valueRanges", [])}
            if name == "batch_update_sheet_values":
                data_items = _as_list(args.get("data"), "data") if isinstance(args.get("data"), str) else args.get("data")
                if not isinstance(data_items, list):
                    raise ValueError("data must be a list")
                data = svc.spreadsheets().values().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={
                        "valueInputOption": args.get("value_input_option", "USER_ENTERED"),
                        "includeValuesInResponse": args.get("include_values_in_response", False),
                        "data": data_items,
                    },
                ).execute()
                return {"updated": True, "result": data}
            if name == "create_named_range":
                named_range = {
                    "name": args["name"],
                    "range": _grid_range(args.get("grid_range")),
                }
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"addNamedRange": {"namedRange": named_range}}]},
                ).execute()
                return {"created": True, "result": data}
            if name == "update_named_range":
                named_range = {
                    "namedRangeId": args["named_range_id"],
                    "name": args["name"],
                    "range": _grid_range(args.get("grid_range")),
                }
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"updateNamedRange": {"namedRange": named_range, "fields": "name,range"}}]},
                ).execute()
                return {"updated": True, "result": data}
            if name == "delete_named_range":
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"deleteNamedRange": {"namedRangeId": args["named_range_id"]}}]},
                ).execute()
                return {"deleted": True, "result": data}
            if name == "add_data_validation":
                rule = _as_dict(args.get("rule"), "rule")
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"setDataValidation": {"range": _grid_range(args.get("grid_range")), "rule": rule, "filteredRowsIncluded": args.get("filtered_rows_included", False)}}]},
                ).execute()
                return {"updated": True, "result": data}
            if name == "set_protected_range":
                protected_range = _as_dict(args.get("protected_range"), "protected_range")
                if not protected_range:
                    raise ValueError("protected_range is required")
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"addProtectedRange": {"protectedRange": protected_range}}]},
                ).execute()
                return {"created": True, "result": data}
            if name == "create_chart":
                chart = _as_dict(args.get("chart"), "chart")
                if not chart:
                    spec = _as_dict(args.get("chart_spec"), "chart_spec")
                    if not spec:
                        raise ValueError("chart or chart_spec is required")
                    chart = {"spec": spec}
                    position = _as_dict(args.get("position"), "position")
                    if position:
                        chart["position"] = position
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"addChart": {"chart": chart}}]},
                ).execute()
                return {"created": True, "result": data}
            if name == "update_chart":
                spec = _as_dict(args.get("chart_spec"), "chart_spec")
                if not spec:
                    raise ValueError("chart_spec is required")
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"updateChartSpec": {"chartId": int(args["chart_id"]), "spec": spec}}]},
                ).execute()
                return {"updated": True, "result": data}
            if name == "create_pivot_table":
                pivot_table = _as_dict(args.get("pivot_table"), "pivot_table")
                if not pivot_table:
                    raise ValueError("pivot_table is required")
                start = _as_dict(args.get("start"), "start")
                if not start:
                    start = {
                        "sheetId": int(args["sheet_id"]),
                        "rowIndex": int(args.get("start_row_index", 0)),
                        "columnIndex": int(args.get("start_column_index", 0)),
                    }
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={
                        "requests": [{
                            "updateCells": {
                                "start": start,
                                "rows": [{"values": [{"pivotTable": pivot_table}]}],
                                "fields": "pivotTable",
                            }
                        }]
                    },
                ).execute()
                return {"created": True, "result": data}
            if name == "format_sheet_range":
                cell_format = _as_dict(args.get("cell_format"), "cell_format")
                if not cell_format:
                    raise ValueError("cell_format is required")
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={
                        "requests": [{
                            "repeatCell": {
                                "range": _grid_range(args.get("grid_range")),
                                "cell": {"userEnteredFormat": cell_format},
                                "fields": "userEnteredFormat",
                            }
                        }]
                    },
                ).execute()
                return {"updated": True, "result": data}
            if name == "add_conditional_formatting":
                rule = _as_dict(args.get("rule"), "rule")
                if not rule:
                    raise ValueError("rule is required")
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"addConditionalFormatRule": {"rule": rule, "index": int(args.get("index", 0))}}]},
                ).execute()
                return {"created": True, "result": data}
            if name == "update_conditional_formatting":
                rule = _as_dict(args.get("rule"), "rule")
                if not rule:
                    raise ValueError("rule is required")
                request: dict[str, Any] = {
                    "index": int(args["index"]),
                    "rule": rule,
                }
                if args.get("new_index") is not None:
                    request["newIndex"] = int(args["new_index"])
                if args.get("sheet_id") is not None:
                    request["sheetId"] = int(args["sheet_id"])
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"updateConditionalFormatRule": request}]},
                ).execute()
                return {"updated": True, "result": data}
            if name == "delete_conditional_formatting":
                request = {"sheetId": int(args["sheet_id"]), "index": int(args["index"])}
                data = svc.spreadsheets().batchUpdate(
                    spreadsheetId=args["spreadsheet_id"],
                    body={"requests": [{"deleteConditionalFormatRule": request}]},
                ).execute()
                return {"deleted": True, "result": data}

        if name in {
            "create_presentation",
            "get_presentation",
            "create_slide",
            "add_textbox",
            "set_text_style",
            "replace_text_everywhere",
            "insert_image_from_url",
            "export_presentation_pdf",
        }:
            if name == "export_presentation_pdf":
                drive = self._svc(user_email, "drive", "v3")
                raw = drive.files().export(fileId=args["presentation_id"], mimeType="application/pdf").execute()
                return {"presentationId": args["presentation_id"], **_json_export(raw, "application/pdf")}
            svc = self._svc(user_email, "slides", "v1")
            if name == "create_presentation":
                data = svc.presentations().create(body={"title": args.get("title", "Untitled Presentation")}).execute()
                return {"created": True, "presentation": data}
            if name == "get_presentation":
                data = svc.presentations().get(presentationId=args["presentation_id"]).execute()
                return {"presentation": data, "slides": [{"slideId": s.get("objectId"), "text": _extract_slide_text(s)} for s in data.get("slides", [])]}
            if name == "create_slide":
                req: dict[str, Any] = {"createSlide": {"slideLayoutReference": {"predefinedLayout": args.get("layout", "TITLE_AND_BODY")}}}
                if args.get("insertion_index") is not None:
                    req["createSlide"]["insertionIndex"] = int(args["insertion_index"])
                data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": [req]}).execute()
                return {"created": True, "result": data}
            if name == "add_textbox":
                object_id = f"textbox_{secrets.token_hex(4)}"
                reqs = [{"createShape": {"objectId": object_id, "shapeType": "TEXT_BOX", "elementProperties": {"pageObjectId": args["page_id"], "size": {"width": {"magnitude": float(args["width"]), "unit": "PT"}, "height": {"magnitude": float(args["height"]), "unit": "PT"}}, "transform": {"scaleX": 1, "scaleY": 1, "translateX": float(args["x"]), "translateY": float(args["y"]), "unit": "PT"}}}}, {"insertText": {"objectId": object_id, "text": args["text"]}}]
                data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": reqs}).execute()
                return {"created": True, "elementId": object_id, "result": data}
            if name == "set_text_style":
                style: dict[str, Any] = {}
                fields: list[str] = []
                for key in ("bold", "italic", "underline", "strikethrough"):
                    if args.get(key) is not None:
                        style[key] = bool(args[key])
                        fields.append(key)
                if args.get("link_url"):
                    style["link"] = {"url": args["link_url"]}
                    fields.append("link")
                if args.get("font_size_pt") is not None:
                    style["fontSize"] = {"magnitude": float(args["font_size_pt"]), "unit": "PT"}
                    fields.append("fontSize")
                color = _optional_color(args.get("foreground_color"), "foreground_color")
                if color:
                    style["foregroundColor"] = color
                    fields.append("foregroundColor")
                if not fields:
                    raise ValueError("At least one style field is required")
                data = svc.presentations().batchUpdate(
                    presentationId=args["presentation_id"],
                    body={"requests": [{
                        "updateTextStyle": {
                            "objectId": args["object_id"],
                            "textRange": _slides_text_range(args.get("start_index"), args.get("end_index")),
                            "style": style,
                            "fields": _field_mask(*fields),
                        }
                    }]},
                ).execute()
                return {"updated": True, "result": data}
            if name == "replace_text_everywhere":
                data = svc.presentations().batchUpdate(
                    presentationId=args["presentation_id"],
                    body={"requests": [{
                        "replaceAllText": {
                            "containsText": {"text": args["contains_text"], "matchCase": args.get("match_case", False)},
                            "replaceText": args["replace_text"],
                        }
                    }]},
                ).execute()
                return {"updated": True, "result": data}
            object_id = str(args.get("object_id") or f"image_{secrets.token_hex(4)}")
            req = {
                "createImage": {
                    "objectId": object_id,
                    "url": args["url"],
                    "elementProperties": {
                        "pageObjectId": args["page_id"],
                        "size": {
                            "width": {"magnitude": float(args["width"]), "unit": "PT"},
                            "height": {"magnitude": float(args["height"]), "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": float(args["x"]),
                            "translateY": float(args["y"]),
                            "unit": "PT",
                        },
                    },
                }
            }
            data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": [req]}).execute()
            return {"created": True, "objectId": object_id, "result": data}

        if name in {
            "list_task_lists",
            "create_task_list",
            "delete_task_list",
            "list_tasks",
            "create_task",
            "update_task",
            "delete_task",
            "complete_task",
            "reopen_task",
            "set_task_due_date",
            "clear_completed_tasks",
        }:
            svc = self._svc(user_email, "tasks", "v1")
            if name == "list_task_lists":
                data = svc.tasklists().list(maxResults=args.get("max_results", 100), pageToken=args.get("page_token")).execute()
                return {"taskLists": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
            if name == "create_task_list":
                return {"created": True, "taskList": svc.tasklists().insert(body={"title": args["title"]}).execute()}
            if name == "delete_task_list":
                svc.tasklists().delete(tasklist=args["task_list_id"]).execute()
                return {"deleted": True, "taskListId": args["task_list_id"]}
            if name == "list_tasks":
                data = svc.tasks().list(tasklist=args["task_list_id"], maxResults=args.get("max_results", 20), pageToken=args.get("page_token"), showCompleted=args.get("show_completed", True), showDeleted=args.get("show_deleted", False), showHidden=args.get("show_hidden", False)).execute()
                return {"tasks": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
            if name == "create_task":
                body: dict[str, Any] = {"title": args["title"]}
                if args.get("notes") is not None:
                    body["notes"] = args["notes"]
                if args.get("due") is not None:
                    body["due"] = _normalize_due(args["due"])
                params: dict[str, Any] = {"tasklist": args["task_list_id"], "body": body}
                if args.get("parent"):
                    params["parent"] = args["parent"]
                return {"created": True, "task": svc.tasks().insert(**params).execute()}
            if name == "update_task":
                body = {}
                for key in ("title", "notes", "status", "due"):
                    if args.get(key) is not None:
                        body[key] = _normalize_due(args[key]) if key == "due" else args[key]
                return {"updated": True, "task": svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body=body).execute()}
            if name == "delete_task":
                svc.tasks().delete(tasklist=args["task_list_id"], task=args["task_id"]).execute()
                return {"deleted": True, "taskId": args["task_id"]}
            if name == "complete_task":
                data = svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body={"status": "completed"}).execute()
                return {"completed": True, "task": data}
            if name == "reopen_task":
                data = svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body={"status": "needsAction"}).execute()
                return {"updated": True, "task": data}
            if name == "set_task_due_date":
                due = _normalize_due(args["due"])
                data = svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body={"due": due}).execute()
                return {"updated": True, "task": data}
            if name == "clear_completed_tasks":
                svc.tasks().clear(tasklist=args["task_list_id"]).execute()
                return {"cleared": True, "taskListId": args["task_list_id"]}

        if name in MASTER_TOKEN_KEEP_TOOL_NAMES and self._keep_master_token.configured:
            return self._dispatch_keep_master_token(name, args)

        if name in ENHANCED_KEEP_TOOL_NAMES:
            raise PermissionError(
                "These Google Keep tools require GOOGLE_KEEP_MASTER_TOKEN and "
                "GOOGLE_KEEP_EMAIL or GOOGLE_DEFAULT_USER_EMAIL."
            )

        if name in OFFICIAL_KEEP_TOOL_NAMES:
            svc = self._svc(user_email, "keep", "v1")
            if name == "list_keep_notes":
                data = svc.notes().list(
                    pageSize=args.get("page_size", 25),
                    pageToken=args.get("page_token"),
                    filter=args.get("filter"),
                ).execute()
                return {"notes": data.get("notes", []), "nextPageToken": data.get("nextPageToken")}
            if name == "get_keep_note":
                return {"note": svc.notes().get(name=args["note_name"]).execute()}
            if name == "create_keep_note":
                list_items = _as_list(args.get("list_items"), "list_items") if isinstance(args.get("list_items"), str) else args.get("list_items")
                if args.get("text") and list_items:
                    raise ValueError("Provide either text or list_items for the note body, not both")
                body: dict[str, Any] = {"title": args["title"]}
                if args.get("text"):
                    body["body"] = {"text": {"text": args["text"]}}
                elif list_items:
                    body["body"] = {
                        "list": {
                            "listItems": [
                                {
                                    "text": {"text": str((item or {}).get("text") or "")},
                                    "checked": bool((item or {}).get("checked", False)),
                                }
                                for item in list_items
                                if isinstance(item, dict)
                            ]
                        }
                    }
                data = svc.notes().create(body=body).execute()
                return {"created": True, "note": data}
            if name == "delete_keep_note":
                svc.notes().delete(name=args["note_name"]).execute()
                return {"deleted": True, "noteName": args["note_name"]}
            if name == "download_keep_attachment":
                raw = svc.media().download(name=args["attachment_name"], mimeType=args["mime_type"]).execute()
                return {"attachmentName": args["attachment_name"], **_json_export(raw, args["mime_type"])}
            if name == "share_keep_note":
                writers = _as_string_list(args.get("writers"), "writers")
                if not writers:
                    raise ValueError("writers is required")
                body = {
                    "requests": [
                        {
                            "parent": args["note_name"],
                            "permission": {"email": writer, "role": "WRITER"},
                        }
                        for writer in writers
                    ]
                }
                data = svc.notes().permissions().batchCreate(parent=args["note_name"], body=body).execute()
                return {"created": True, "result": data}
            if name == "unshare_keep_note":
                targets = set(_as_string_list(args.get("emails_or_groups"), "emails_or_groups"))
                if not targets:
                    raise ValueError("emails_or_groups is required")
                note = svc.notes().get(name=args["note_name"]).execute()
                permission_names: list[str] = []
                for permission in note.get("permissions", []):
                    email = str(permission.get("email") or "").strip()
                    permission_name = str(permission.get("name") or "").strip()
                    if email in targets or permission_name in targets:
                        permission_names.append(permission_name)
                if not permission_names:
                    raise ValueError("No matching Keep permissions were found")
                data = svc.notes().permissions().batchDelete(parent=args["note_name"], body={"names": permission_names}).execute()
                return {"deleted": True, "result": data, "permissionNames": permission_names}
            note = svc.notes().get(name=args["note_name"]).execute()
            return {"noteName": args["note_name"], "permissions": note.get("permissions", [])}

        if name in {"list_contacts", "search_contacts", "create_contact", "update_contact", "delete_contact"}:
            svc = self._svc(user_email, "people", "v1")
            default_fields = "names,emailAddresses,phoneNumbers,organizations,metadata"
            if name == "list_contacts":
                params: dict[str, Any] = {
                    "resourceName": "people/me",
                    "personFields": args.get("person_fields", default_fields),
                    "pageSize": args.get("page_size", 100),
                    "pageToken": args.get("page_token"),
                }
                if args.get("sort_order"):
                    params["sortOrder"] = args["sort_order"]
                if args.get("sync_token"):
                    params["syncToken"] = args["sync_token"]
                data = svc.people().connections().list(**params).execute()
                return {
                    "contacts": data.get("connections", []),
                    "nextPageToken": data.get("nextPageToken"),
                    "nextSyncToken": data.get("nextSyncToken"),
                }
            if name == "search_contacts":
                params = {
                    "query": args["query"],
                    "pageSize": args.get("page_size", 10),
                    "readMask": args.get("read_mask", default_fields),
                }
                sources = _as_string_list(args.get("sources"), "sources")
                if sources:
                    params["sources"] = sources
                data = svc.people().searchContacts(**params).execute()
                return {"results": data.get("results", [])}
            if name == "create_contact":
                person = _as_dict(args.get("person"), "person")
                if not person:
                    raise ValueError("person is required")
                data = svc.people().createContact(
                    personFields=args.get("person_fields", default_fields),
                    body=person,
                ).execute()
                return {"created": True, "person": data}
            if name == "update_contact":
                person = _as_dict(args.get("person"), "person")
                if not person:
                    raise ValueError("person is required")
                update_person_fields = str(args.get("update_person_fields") or ",".join(sorted(person.keys()))).strip(",")
                if not update_person_fields:
                    raise ValueError("update_person_fields is required")
                person["resourceName"] = args["resource_name"]
                if not person.get("etag"):
                    current = svc.people().get(resourceName=args["resource_name"], personFields=update_person_fields).execute()
                    if current.get("etag"):
                        person["etag"] = current["etag"]
                data = svc.people().updateContact(
                    resourceName=args["resource_name"],
                    updatePersonFields=update_person_fields,
                    personFields=args.get("person_fields", default_fields),
                    body=person,
                ).execute()
                return {"updated": True, "person": data}
            svc.people().deleteContact(resourceName=args["resource_name"]).execute()
            return {"deleted": True, "resourceName": args["resource_name"]}

        if name == "batch_update_form":
            svc = self._svc(user_email, "forms", "v1")
            body: dict[str, Any] = {
                "requests": _as_list(args.get("requests"), "requests") if isinstance(args.get("requests"), str) else args.get("requests"),
            }
            if not isinstance(body["requests"], list):
                raise ValueError("requests must be a list")
            if args.get("include_form_in_response") is not None:
                body["includeFormInResponse"] = bool(args["include_form_in_response"])
            write_control = _as_dict(args.get("write_control"), "write_control")
            if write_control:
                body["writeControl"] = write_control
            data = svc.forms().batchUpdate(formId=args["form_id"], body=body).execute()
            return {"updated": True, "result": data}

        if name in {"list_conference_records", "get_conference_record"}:
            svc = self._svc(user_email, "meet", "v2")
            if name == "list_conference_records":
                data = svc.conferenceRecords().list(
                    pageSize=args.get("page_size", 25),
                    pageToken=args.get("page_token"),
                    filter=args.get("filter"),
                ).execute()
                return {"conferenceRecords": data.get("conferenceRecords", []), "nextPageToken": data.get("nextPageToken")}
            return {"conferenceRecord": svc.conferenceRecords().get(name=args["name"]).execute()}

        raise NotImplementedError(f"Tool '{name}' is not implemented")


def _register_tools(server: FastMCP, runtime: GoogleRuntime, manifest: list[dict[str, Any]]) -> None:
    for spec in manifest:
        name = str(spec.get("name") or "").strip()
        if not name:
            continue
        params = spec.get("parameters") or {"type": "object", "properties": {}, "additionalProperties": True}
        params = json.loads(json.dumps(params))
        properties = params.get("properties")
        if isinstance(properties, dict) and "user_google_email" in properties:
            original = str(properties["user_google_email"].get("description") or "The user's Google email address.")
            properties["user_google_email"]["description"] = (
                f"{original} Optional when GOOGLE_DEFAULT_USER_EMAIL or GOOGLE_IMPERSONATED_USER "
                "is configured, service-account auth is used, or GOOGLE_API_KEY is being used for "
                "public-data requests."
            )
            required = [item for item in params.get("required", []) if item != "user_google_email"]
            if required:
                params["required"] = required
            elif "required" in params:
                params.pop("required")
        desc = str(spec.get("description") or "")

        async def _fn(_name: str = name, **kwargs: Any) -> dict[str, Any]:
            try:
                return await runtime.dispatch(_name, kwargs)
            except Exception as exc:
                return {"isError": True, "error": str(exc)}

        server.add_tool(
            FunctionTool(
                name=name,
                description=desc,
                parameters=params,
                output_schema={"type": "object", "additionalProperties": True},
                fn=_fn,
            )
        )


def _health_payload(
    credential_store: CredentialStore,
    service_accounts: ServiceAccountStore,
    keep_backend: GoogleKeepMasterTokenBackend,
) -> dict[str, Any]:
    auth_sources: list[str] = []
    if service_accounts.configured:
        auth_sources.append("service_account")
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
        "serviceAccountConfigured": service_accounts.configured,
        "defaultImpersonatedUser": service_accounts.default_subject or None,
        "defaultUserEmail": _runtime_env("GOOGLE_DEFAULT_USER_EMAIL") or None,
        "keepMasterTokenConfigured": keep_backend.configured,
        "keepManagedLabel": keep_backend.managed_label_name if keep_backend.configured else None,
        "keepUnsafeMode": keep_backend.unsafe_mode,
        "legacyCredentialDecryption": bool(_runtime_env("MASTER_KEY")),
    }


manifest = _load_manifest()
credential_store = CredentialStore()
service_account_store = ServiceAccountStore()
runtime = GoogleRuntime(credential_store, service_account_store)

api_keys = _load_api_keys()
auth = StaticApiKeyVerifier(api_keys=api_keys, base_url=_runtime_env("BASE_URL")) if api_keys else None
server = FastMCP("google-workspace-mcp", auth=auth)
mcp = server
_register_tools(server, runtime, manifest)


@server.custom_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root_health(_request):
    return JSONResponse(_health_payload(credential_store, service_account_store, runtime._keep_master_token))


@server.custom_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
async def health(_request):
    return JSONResponse(_health_payload(credential_store, service_account_store, runtime._keep_master_token))


@server.custom_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
async def healthz(_request):
    return JSONResponse(_health_payload(credential_store, service_account_store, runtime._keep_master_token))


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
