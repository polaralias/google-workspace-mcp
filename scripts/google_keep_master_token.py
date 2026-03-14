from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

import gpsoauth

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_server import load_env_files  # noqa: E402


def _default_env_path() -> Path:
    return REPO_ROOT / ".env"


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

    path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exchange a Google EmbeddedSetup oauth_token cookie for a Google master token used by gkeepapi."
    )
    parser.add_argument(
        "--email",
        default="",
        help="Google account email. Defaults to GOOGLE_KEEP_EMAIL or GOOGLE_DEFAULT_USER_EMAIL from .env.",
    )
    parser.add_argument(
        "--oauth-token",
        default="",
        help="The oauth_token cookie value copied from https://accounts.google.com/EmbeddedSetup.",
    )
    parser.add_argument(
        "--android-id",
        default="",
        help="16-char hex Android ID to use for the exchange. Defaults to a random one.",
    )
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="Write GOOGLE_KEEP_EMAIL and GOOGLE_KEEP_MASTER_TOKEN to the repo-local .env file.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_default_env_path(),
        help="Env file to update when --update-env is used. Defaults to the repo-local .env.",
    )
    parser.add_argument(
        "--print-response",
        action="store_true",
        help="Print the full gpsoauth exchange response for debugging.",
    )
    return parser


def main() -> int:
    load_env_files()
    args = build_parser().parse_args()

    email = str(args.email or os.getenv("GOOGLE_KEEP_EMAIL") or os.getenv("GOOGLE_DEFAULT_USER_EMAIL") or "").strip().lower()
    if not email:
        raise SystemExit("Missing --email. Set GOOGLE_KEEP_EMAIL or GOOGLE_DEFAULT_USER_EMAIL, or pass --email.")

    oauth_token = str(args.oauth_token or "").strip()
    if not oauth_token:
        raise SystemExit("Missing --oauth-token. Copy the oauth_token cookie value from EmbeddedSetup and pass it here.")

    android_id = str(args.android_id or "").strip().lower() or secrets.token_hex(8)

    response = gpsoauth.exchange_token(email, oauth_token, android_id)
    if args.print_response:
        print(json.dumps(response, indent=2, sort_keys=True))

    master_token = str(response.get("Token") or "").strip()
    if not master_token:
        debug = json.dumps(response, indent=2, sort_keys=True)
        raise SystemExit(
            "Master-token exchange failed. gpsoauth did not return a Token field.\n"
            f"Response:\n{debug}"
        )

    print(f"email={email}")
    print(f"android_id={android_id}")
    print(f"master_token={master_token}")

    if args.update_env:
        env_path = args.env_file.expanduser()
        if not env_path.is_absolute():
            env_path = REPO_ROOT / env_path
        _update_env_file(
            env_path,
            {
                "GOOGLE_KEEP_EMAIL": email,
                "GOOGLE_KEEP_MASTER_TOKEN": master_token,
            },
        )
        print(f"updated_env={env_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
