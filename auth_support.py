from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastmcp.server.auth import AccessToken, TokenVerifier
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials


RUNTIME_PLACEHOLDER_RE = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*\}$")


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
