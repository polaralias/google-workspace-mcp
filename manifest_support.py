from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastmcp.tools import FunctionTool


def repo_root(current_file: str) -> Path:
    return Path(current_file).resolve().parent


def load_manifest(root: Path) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    manifest_paths = sorted(root.glob("tool_manifest_google*.json"))
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


def register_tools(
    tool_server: Any,
    dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    manifest: list[dict[str, Any]],
) -> None:
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
                f"{original} Optional when GOOGLE_DEFAULT_USER_EMAIL is configured or "
                "GOOGLE_API_KEY is being used for public-data requests."
            )
            required = [item for item in params.get("required", []) if item != "user_google_email"]
            if required:
                params["required"] = required
            elif "required" in params:
                params.pop("required")
        desc = str(spec.get("description") or "")

        async def _fn(_name: str = name, **kwargs: Any) -> dict[str, Any]:
            try:
                return await dispatch(_name, kwargs)
            except Exception as exc:
                return {"isError": True, "error": str(exc)}

        tool_server.add_tool(
            FunctionTool(
                name=name,
                description=desc,
                parameters=params,
                output_schema={"type": "object", "additionalProperties": True},
                fn=_fn,
            )
        )
