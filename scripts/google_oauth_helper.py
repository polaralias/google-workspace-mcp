from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_server import load_env_files  # noqa: E402

OPENID_SCOPE = "openid"
USERINFO_EMAIL_SCOPE = "https://www.googleapis.com/auth/userinfo.email"
SERVICE_SCOPES: dict[str, list[str]] = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "chat": [
        "https://www.googleapis.com/auth/chat.spaces",
        "https://www.googleapis.com/auth/chat.memberships",
        "https://www.googleapis.com/auth/chat.messages",
    ],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "forms": ["https://www.googleapis.com/auth/forms.body"],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.settings.basic",
    ],
    "keep": ["https://www.googleapis.com/auth/keep"],
    "keep_readonly": ["https://www.googleapis.com/auth/keep.readonly"],
    "meet": ["https://www.googleapis.com/auth/meetings.space.readonly"],
    "people": ["https://www.googleapis.com/auth/contacts"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "tasks": ["https://www.googleapis.com/auth/tasks"],
    "userinfo": [OPENID_SCOPE, USERINFO_EMAIL_SCOPE],
}
PROFILE_SERVICES: dict[str, list[str]] = {
    "calendar": ["calendar", "userinfo"],
    "chat": ["chat", "userinfo"],
    "docs": ["docs", "userinfo"],
    "drive": ["drive", "userinfo"],
    "forms": ["forms", "userinfo"],
    "gmail": ["gmail", "userinfo"],
    "keep": ["keep", "userinfo"],
    "keep-readonly": ["keep_readonly", "userinfo"],
    "meet": ["meet", "userinfo"],
    "people": ["people", "userinfo"],
    "personal": [
        "calendar",
        "docs",
        "drive",
        "forms",
        "gmail",
        "keep",
        "meet",
        "people",
        "sheets",
        "slides",
        "tasks",
        "userinfo",
    ],
    "sheets": ["sheets", "userinfo"],
    "slides": ["slides", "userinfo"],
    "tasks": ["tasks", "userinfo"],
    "workspace": [
        "calendar",
        "chat",
        "docs",
        "drive",
        "forms",
        "gmail",
        "keep",
        "meet",
        "people",
        "sheets",
        "slides",
        "tasks",
        "userinfo",
    ],
}
DEFAULT_CREDENTIALS_DIR = REPO_ROOT / ".oauth"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _credential_store_dir() -> Path:
    configured = os.getenv("GOOGLE_MCP_CREDENTIALS_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else REPO_ROOT / path
    return DEFAULT_CREDENTIALS_DIR


def _client_config_from_env() -> dict[str, object] | None:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "http://127.0.0.1",
                "http://localhost",
            ],
        }
    }


def _scopes_for_profile(profile: str, without: list[str]) -> list[str]:
    services = [service for service in PROFILE_SERVICES[profile] if service not in set(without)]
    scopes: list[str] = []
    for service in services:
        scopes.extend(SERVICE_SCOPES[service])
    return _dedupe(scopes)


def _update_env_file(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = updates.copy()
    rewritten: list[str] = []
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            rewritten.append(line)
            continue
        key, _value = line.split("=", 1)
        if key in remaining:
            rewritten.append(f"{key}={remaining.pop(key)}")
        else:
            rewritten.append(line)

    for key, value in remaining.items():
        rewritten.append(f"{key}={value}")

    contents = "\n".join(rewritten).rstrip() + "\n"
    path.write_text(contents, encoding="utf-8")


def _env_path_value(path: Path) -> str:
    try:
        return os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    except ValueError:
        return str(path)


def _client_metadata(credentials) -> tuple[str, str]:
    client_id = getattr(credentials, "client_id", "") or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = getattr(credentials, "client_secret", "") or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    return client_id, client_secret


def _discover_email(credentials) -> str:
    oauth2 = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
    profile = oauth2.userinfo().get().execute()
    email = str(profile.get("email") or "").strip().lower()
    if not email:
        raise SystemExit("OAuth succeeded, but the Google account email could not be determined.")
    return email


def _write_credentials(path: Path, credentials) -> None:
    client_id, client_secret = _client_metadata(credentials)
    if not client_id or not client_secret:
        raise SystemExit("OAuth credentials were created, but the client ID/secret metadata is incomplete.")

    payload = {
        "oauth_client_id": client_id,
        "oauth_client_secret": client_secret,
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "scopes": list(credentials.scopes or []),
    }
    if getattr(credentials, "expiry", None) is not None:
        payload["expiry"] = credentials.expiry.isoformat()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-time OAuth helper for Google Workspace MCP user credentials")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_SERVICES),
        default="gmail",
        help="Scope bundle to request. Use 'gmail' for personal mail only, 'keep' for full Keep access, 'keep-readonly' for Keep read access, 'personal' for broader personal Google data, or 'workspace' for the full supported Workspace toolset.",
    )
    parser.add_argument(
        "--without",
        action="append",
        choices=sorted(service for service in SERVICE_SCOPES if service != "userinfo"),
        default=[],
        help="Exclude one or more service scope groups from the selected profile. Repeat as needed, for example --without keep --without meet.",
    )
    parser.add_argument(
        "--client-secrets-file",
        type=Path,
        help="Path to a Google OAuth desktop client JSON file. If omitted, GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are used.",
    )
    parser.add_argument("--listen-host", default="127.0.0.1", help="Local host to bind for the temporary OAuth callback server.")
    parser.add_argument("--listen-port", type=int, default=8765, help="Local port for the temporary OAuth callback server.")
    parser.add_argument("--no-browser", action="store_true", help="Print the auth URL instead of opening a browser automatically.")
    parser.add_argument(
        "--skip-env-update",
        action="store_true",
        help="Do not update the repo-local .env with GOOGLE_MCP_CREDENTIALS_DIR and GOOGLE_DEFAULT_USER_EMAIL.",
    )
    return parser


def main() -> int:
    load_env_files()
    args = build_parser().parse_args()
    scopes = _scopes_for_profile(args.profile, args.without)

    if args.client_secrets_file:
        flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets_file), scopes=scopes)
    else:
        client_config = _client_config_from_env()
        if client_config is None:
            raise SystemExit(
                "Missing OAuth client configuration. Provide --client-secrets-file or set "
                "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET."
            )
        flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)

    credentials = flow.run_local_server(
        host=args.listen_host,
        port=args.listen_port,
        open_browser=not args.no_browser,
        authorization_prompt_message="Open this URL to authorize Google Workspace MCP: {url}",
        success_message="Google authorization completed. You can close this window.",
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    email = _discover_email(credentials)
    credentials_dir = _credential_store_dir()
    credential_path = credentials_dir / f"{email}.json"
    _write_credentials(credential_path, credentials)

    if not args.skip_env_update:
        env_updates = {
            "GOOGLE_MCP_CREDENTIALS_DIR": _env_path_value(credentials_dir),
            "GOOGLE_DEFAULT_USER_EMAIL": email,
        }
        _update_env_file(REPO_ROOT / ".env", env_updates)

    print(f"stored_email={email}")
    print(f"credentials_file={credential_path}")
    print(f"scope_profile={args.profile}")
    if args.without:
        print("excluded_services=" + ",".join(args.without))
    print("next_step=restart Google Workspace MCP to pick up the stored OAuth credential")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
