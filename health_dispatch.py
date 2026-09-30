"""Bounded Google Health API v4 dispatch over the checked-in data-type catalog."""

from __future__ import annotations

import json
from importlib.resources import files
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEALTH_BASE = "https://health.googleapis.com/v4"
_catalog_path = Path(__file__).parent / "health_catalog.json"
_catalog_text = _catalog_path.read_text(encoding="utf-8") if _catalog_path.exists() else files("google_workspace_mcp_data").joinpath("health_catalog.json").read_text(encoding="utf-8")
HEALTH_CATALOG = json.loads(_catalog_text)["data_types"]
HEALTH_TOOL_NAMES = {
    "health_list_data_points", "health_get_data_point", "health_create_data_point",
    "health_update_data_point", "health_delete_data_points", "health_reconcile_data_points",
    "health_rollup_data_points", "health_daily_rollup_data_points",
    "health_export_exercise_tcx", "health_get_identity", "health_get_profile",
    "health_update_profile", "health_get_settings", "health_update_settings",
    "health_get_irn_profile", "health_catalog",
}
_POINT_ID = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")
_FIELD_MASK = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*(?:,[A-Za-z][A-Za-z0-9_.]*)*$")
_READ_ACTIONS = {"list", "get", "reconcile", "rollup", "dailyRollup", "exportExerciseTcx"}
_WRITE_ACTIONS = {"create", "update", "batchDelete"}
_DATA_SOURCE_FAMILIES = {
    "all-sources", "google-wearables", "google-sources", "self-sources",
}
_USER_ACTIONS = {
    "health_get_identity": ("GET", "identity", "activity_and_fitness.readonly"),
    "health_get_profile": ("GET", "profile", "profile.readonly"),
    "health_update_profile": ("PATCH", "profile", "profile.writeonly"),
    "health_get_settings": ("GET", "settings", "settings.readonly"),
    "health_update_settings": ("PATCH", "settings", "settings.writeonly"),
    "health_get_irn_profile": ("GET", "irnProfile", "irn.readonly"),
}


def _bounded_body(value: Any, *, maximum: int = 65536) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("body must be a JSON object")
    if len(json.dumps(value, allow_nan=False)) > maximum:
        raise ValueError("body is too large")
    return value


def _point_path(data_type: str, point_id: str | None = None) -> str:
    path = f"users/me/dataTypes/{data_type}/dataPoints"
    if point_id is not None:
        if not _POINT_ID.fullmatch(point_id):
            raise ValueError("invalid data point ID")
        path += "/" + quote(point_id, safe="._~-")
    return path


def _scope_for(spec: dict[str, Any], action: str) -> str:
    suffix = ".readonly" if action in _READ_ACTIONS else ".writeonly"
    scopes = [scope for scope in spec["scopes"] if scope.endswith(suffix)]
    if not scopes:
        raise PermissionError(f"Google Health {action} scope is unavailable for this data type")
    return scopes[0]


def _credentials(store: Any, email: str, scope: str) -> Any:
    if not email:
        raise PermissionError("Google Health requires user_google_email or GOOGLE_DEFAULT_USER_EMAIL")
    credentials = store.get(email)
    if credentials is None:
        raise PermissionError(f"Google Health OAuth credentials are missing for {email}")
    granted = credentials.granted_scopes
    available = set(granted if granted is not None else (credentials.scopes or []))
    if scope not in available:
        raise PermissionError(f"Google Health OAuth scope is missing: {scope}")
    return credentials


def _request(credentials: Any, method: str, path: str, *, params: dict[str, Any] | None = None, body: dict[str, Any] | None = None, media: bool = False) -> dict[str, Any]:
    with AuthorizedSession(credentials) as session:
        session.mount(
            HEALTH_BASE,
            HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods={"GET"}, respect_retry_after_header=True)),
        )
        response = session.request(method, f"{HEALTH_BASE}/{path}", params=params, json=body, timeout=30)
    if response.status_code >= 400:
        reason = "unknown"
        try:
            error = response.json().get("error", {})
            reason = str(error.get("status") or error.get("code") or reason)
        except (ValueError, AttributeError):
            pass
        raise RuntimeError(f"Google Health API returned HTTP {response.status_code} ({reason})")
    if media:
        if len(response.content) > 1_000_000:
            raise ValueError("TCX export exceeds the 1 MB MCP response limit")
        return {"tcx": response.text}
    if not response.content:
        return {}
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Google Health returned a non-object response")
    return payload


def dispatch_health(store: Any, default_email: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "health_catalog":
        return {"dataTypes": HEALTH_CATALOG}
    email = str(args.get("user_google_email") or default_email or "").strip().lower()
    if name in _USER_ACTIONS:
        method, resource, scope_suffix = _USER_ACTIONS[name]
        scope = "https://www.googleapis.com/auth/googlehealth." + scope_suffix
        credentials = _credentials(store, email, scope)
        body = _bounded_body(args.get("body")) if method == "PATCH" else None
        params = None
        if method == "PATCH" and args.get("update_mask"):
            mask = str(args["update_mask"])
            if not _FIELD_MASK.fullmatch(mask):
                raise ValueError("invalid update mask")
            params = {"updateMask": mask}
        return _request(credentials, method, f"users/me/{resource}", params=params, body=body)

    data_type = str(args.get("data_type") or "")
    spec = HEALTH_CATALOG.get(data_type)
    if spec is None:
        raise ValueError("unknown Google Health data type")
    action_by_tool = {
        "health_list_data_points": "list", "health_get_data_point": "get",
        "health_create_data_point": "create", "health_update_data_point": "update",
        "health_delete_data_points": "batchDelete", "health_reconcile_data_points": "reconcile",
        "health_rollup_data_points": "rollup", "health_daily_rollup_data_points": "dailyRollup",
        "health_export_exercise_tcx": "exportExerciseTcx",
    }
    action = action_by_tool.get(name)
    if action is None:
        raise ValueError("unknown Google Health tool")
    if action != "exportExerciseTcx" and action not in spec["operations"]:
        raise ValueError(f"Google Health {action} is not supported for {data_type}")
    if action == "exportExerciseTcx" and data_type != "exercise":
        raise ValueError("TCX export requires the exercise data type")
    credentials = _credentials(store, email, _scope_for(spec, action))
    path = _point_path(data_type)
    point_id = args.get("point_id")
    if action in {"get", "update", "exportExerciseTcx"}:
        if not isinstance(point_id, str) or not point_id:
            raise ValueError("point_id is required")
        path = _point_path(data_type, point_id)
    if action == "exportExerciseTcx":
        return _request(credentials, "GET", path + ":exportExerciseTcx", params={"alt": "media", "partialData": bool(args.get("partial_data", False))}, media=True)
    if action == "batchDelete":
        ids = args.get("point_ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= 100 or not all(isinstance(item, str) for item in ids):
            raise ValueError("point_ids must contain 1 to 100 data point IDs")
        names = [_point_path(data_type, item) for item in ids]
        return _request(credentials, "POST", path + ":batchDelete", body={"names": names})
    if action in {"create", "update"}:
        body = _bounded_body(args.get("body"))
        field = spec["field"]
        allowed = {field, "dataSource", "name"} if action == "update" else {field, "dataSource"}
        if field not in body or not isinstance(body[field], dict) or set(body) - allowed:
            raise ValueError(f"body must contain only the {field} data point and optional dataSource")
        if action == "update" and "name" in body and body["name"] != path:
            raise ValueError("body name does not match the selected data point")
        return _request(credentials, "PATCH" if action == "update" else "POST", path, body=body)
    if action in {"rollup", "dailyRollup"}:
        return _request(credentials, "POST", path + (":rollUp" if action == "rollup" else ":dailyRollUp"), body=_bounded_body(args.get("body")))
    params: dict[str, Any] = {}
    if action in {"list", "reconcile"}:
        if args.get("filter"):
            filter_value = str(args["filter"])
            if len(filter_value) > 2000 or "\n" in filter_value or "\r" in filter_value:
                raise ValueError("invalid Health filter")
            params["filter"] = filter_value
        if args.get("data_source_family"):
            family = str(args["data_source_family"])
            if family not in _DATA_SOURCE_FAMILIES:
                raise ValueError("invalid data source family")
            params["dataSourceFamily"] = f"users/me/dataSourceFamilies/{family}"
    if action == "list":
        page_size = args.get("page_size", 25)
        limit = 25 if data_type in {"exercise", "sleep"} else 1000
        if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= limit:
            raise ValueError(f"page_size must be between 1 and {limit}")
        params["pageSize"] = page_size
        if args.get("page_token"):
            token = str(args["page_token"])
            if len(token) > 2048:
                raise ValueError("page_token is too long")
            params["pageToken"] = token
    return _request(credentials, "GET", path, params=params or None)
