import asyncio
import os
import warnings
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import server


LIVE_TEST_FLAG = "GOOGLE_WORKSPACE_MCP_RUN_LIVE_TESTS"
LIVE_TEST_EMAIL = "GOOGLE_WORKSPACE_MCP_LIVE_TEST_EMAIL"

warnings.filterwarnings("ignore", category=ResourceWarning, message=r"unclosed <ssl\.SSLSocket.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"gpsoauth(\..*)?$")
warnings.simplefilter("ignore", ResourceWarning)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_credentials_dir() -> Path:
    return _repo_root() / ".oauth"


def _discover_email(credentials_dir: Path) -> str | None:
    configured = os.getenv(LIVE_TEST_EMAIL) or os.getenv("GOOGLE_DEFAULT_USER_EMAIL")
    if configured:
        return configured.strip().lower() or None

    candidates = sorted(credentials_dir.glob("*.json"))
    if len(candidates) == 1:
        return candidates[0].stem.lower()
    return None


def require_live_google_workspace(testcase):
    if os.getenv(LIVE_TEST_FLAG, "").strip().lower() != "true":
        testcase.skipTest(f"set {LIVE_TEST_FLAG}=true to run live Google Workspace integration tests")

    configured_dir = os.getenv("GOOGLE_MCP_CREDENTIALS_DIR", "").strip()
    credentials_dir = Path(configured_dir).expanduser() if configured_dir else _default_credentials_dir()
    if not credentials_dir.exists():
        testcase.skipTest(f"credentials dir not found: {credentials_dir}")

    email = _discover_email(credentials_dir)
    if not email:
        testcase.skipTest(
            f"set {LIVE_TEST_EMAIL} or GOOGLE_DEFAULT_USER_EMAIL so live tests know which stored OAuth user to use"
        )

    credential_file = credentials_dir / f"{email}.json"
    if not credential_file.exists():
        testcase.skipTest(f"stored OAuth credential not found: {credential_file}")

    return {"credentials_dir": str(credentials_dir), "email": email}


def live_credentials(config: dict[str, str]):
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_MCP_CREDENTIALS_DIR": config["credentials_dir"],
            "GOOGLE_DEFAULT_USER_EMAIL": config["email"],
        },
        clear=False,
    ):
        store = server.CredentialStore()
        creds = store.get(config["email"])
        if creds is None:
            raise RuntimeError(f"stored OAuth credential unavailable for {config['email']}")
        return creds


def live_credential_scopes(config: dict[str, str]) -> set[str]:
    creds = live_credentials(config)
    return set(getattr(creds, "scopes", None) or [])


def require_live_scopes(testcase, required_scopes: list[str]):
    config = require_live_google_workspace(testcase)
    available = live_credential_scopes(config)
    missing = [scope for scope in required_scopes if scope not in available]
    if missing:
        testcase.skipTest(f"stored OAuth credential is missing required scopes: {', '.join(missing)}")
    return config


def require_live_api_key(testcase):
    require_live_google_workspace(testcase)
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        testcase.skipTest("set GOOGLE_API_KEY to run live API-key integration tests")
    return {"api_key": api_key}


def require_live_keep_master_token(testcase):
    config = require_live_google_workspace(testcase)
    keep_email = (os.getenv("GOOGLE_KEEP_EMAIL") or config["email"]).strip().lower()
    keep_token = os.getenv("GOOGLE_KEEP_MASTER_TOKEN", "").strip()
    if not keep_token:
        testcase.skipTest("set GOOGLE_KEEP_MASTER_TOKEN to run live Keep master-token integration tests")
    return {**config, "keep_email": keep_email, "keep_token": keep_token}


def live_google_client(config: dict[str, str], service_name: str, version: str):
    return build(service_name, version, credentials=live_credentials(config), cache_discovery=False)


def maybe_skip_http_error(testcase, exc: Exception, prefix: str):
    if not isinstance(exc, HttpError):
        raise exc

    status = getattr(exc.resp, "status", None)
    message = str(exc)
    skip_fragments = (
        "insufficient authentication scopes",
        "access not configured",
        "api has not been used",
        "permission denied",
        "requested entity was not found",
        "not found",
        "service disabled",
        "does not have permission",
        "caller does not have permission",
    )
    lowered = message.lower()
    if status in {403, 404, 501} or any(fragment in lowered for fragment in skip_fragments):
        testcase.skipTest(f"{prefix}: {message}")
    raise exc


@contextmanager
def live_runtime(config: dict[str, str], extra_env: dict[str, str] | None = None):
    env = {
        "GOOGLE_MCP_CREDENTIALS_DIR": config["credentials_dir"],
        "GOOGLE_DEFAULT_USER_EMAIL": config["email"],
    }
    if extra_env:
        env.update(extra_env)
    with patch.dict(
        "os.environ",
        env,
        clear=False,
    ):
        loop = asyncio.get_running_loop()
        previous_debug = loop.get_debug()
        loop.set_debug(False)
        runtime = server.GoogleRuntime(server.CredentialStore())
        created_services = []
        original_svc = runtime._svc

        def _tracked_svc(user_email: str | None, api: str, version: str):
            svc = original_svc(user_email, api, version)
            created_services.append(svc)
            return svc

        runtime._svc = _tracked_svc  # type: ignore[method-assign]
        try:
            yield runtime
        finally:
            for svc in created_services:
                close = getattr(svc, "close", None)
                if callable(close):
                    close()
            loop.set_debug(previous_debug)


@contextmanager
def api_key_runtime(config: dict[str, str]):
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_MCP_CREDENTIALS_DIR": str(_repo_root() / ".missing-oauth"),
            "GOOGLE_DEFAULT_USER_EMAIL": "",
            "GOOGLE_KEEP_EMAIL": "",
            "GOOGLE_KEEP_MASTER_TOKEN": "",
            "GOOGLE_API_KEY": config["api_key"],
        },
        clear=False,
    ):
        loop = asyncio.get_running_loop()
        previous_debug = loop.get_debug()
        loop.set_debug(False)
        runtime = server.GoogleRuntime(server.CredentialStore())
        created_services = []
        original_svc = runtime._svc

        def _tracked_svc(user_email: str | None, api: str, version: str):
            svc = original_svc(user_email, api, version)
            created_services.append(svc)
            return svc

        runtime._svc = _tracked_svc  # type: ignore[method-assign]
        try:
            yield runtime
        finally:
            for svc in created_services:
                close = getattr(svc, "close", None)
                if callable(close):
                    close()
            loop.set_debug(previous_debug)


def live_google_clients(config: dict[str, str]):
    creds = live_credentials(config)
    return {
        "calendar": build("calendar", "v3", credentials=creds, cache_discovery=False),
        "drive": build("drive", "v3", credentials=creds, cache_discovery=False),
        "forms": build("forms", "v1", credentials=creds, cache_discovery=False),
        "gmail": build("gmail", "v1", credentials=creds, cache_discovery=False),
        "keep": build("keep", "v1", credentials=creds, cache_discovery=False),
        "meet": build("meet", "v2", credentials=creds, cache_discovery=False),
        "sheets": build("sheets", "v4", credentials=creds, cache_discovery=False),
    }
