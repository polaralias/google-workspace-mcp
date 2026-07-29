from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from manifest_support import load_manifest


def _manifest_paths() -> list[Path]:
    return sorted(REPO_ROOT.glob("tool_manifest_google*.json"))


def _specs_by_name() -> dict[str, dict[str, Any]]:
    merged = {str(spec.get("name") or "").strip(): spec for spec in load_manifest(REPO_ROOT)}
    return {name: spec for name, spec in merged.items() if name}


def _source_manifests() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in _manifest_paths():
        data = json.loads(path.read_text(encoding="utf-8"))
        for spec in data.get("tools") or []:
            name = str((spec or {}).get("name") or "").strip()
            if name:
                sources[name] = path.name
    return sources


def _format_param(name: str, schema: dict[str, Any], required: set[str]) -> str:
    param_type = schema.get("type", "any")
    default = schema.get("default")
    default_text = f" default `{default}`" if default is not None else ""
    required_text = "required" if name in required else "optional"
    description = str(schema.get("description") or "").strip()
    suffix = f" | {description}" if description else ""
    return f"- `{name}` | `{param_type}` | {required_text}{default_text}{suffix}"


def render_tool_reference() -> str:
    specs = _specs_by_name()
    sources = _source_manifests()
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for name, spec in specs.items():
        grouped[sources[name]].append((name, spec))

    total = len(specs)
    lines = [
        "---",
        'type: "Reference"',
        'title: "Tool Reference"',
        'description: "Documents Tool Reference for the google-workspace-mcp repository."',
        "timestamp: 2026-07-28T21:55:36Z",
        "authority: canonical",
        "verification: untested",
        "owner: polaralias",
        "tags:",
        "  - google-workspace-mcp",
        "  - reference",
        "navigation:",
        "  role: reference",
        "  order: 200",
        "---",
        "# Tool Reference",
        "",
        f"This reference is generated from the public Google Workspace tool manifests and covers all {total} unique tools exposed by the server.",
        "",
        "Parameter format notes:",
        "- `required` means the manifest schema marks the field as mandatory.",
        "- `default ...` only appears when the manifest defines a default value.",
        "- Many tools accept `user_google_email` to select the authenticated user context explicitly.",
        "",
    ]

    for manifest_name in sorted(grouped):
        lines.extend(
            [
                f"## `{manifest_name}`",
                "",
                f"Source manifest: `{manifest_name}`",
                "",
            ]
        )
        for tool_name, spec in sorted(grouped[manifest_name], key=lambda item: item[0]):
            params = spec.get("parameters") or {}
            properties = params.get("properties") or {}
            required = set(params.get("required") or [])
            lines.extend(
                [
                    f"### `{tool_name}`",
                    "",
                    str(spec.get("description") or "").strip(),
                    "",
                    "- Parameters:",
                ]
            )
            if properties:
                for param_name, schema in properties.items():
                    lines.append(_format_param(param_name, schema or {}, required))
            else:
                lines.append("- none")
            lines.append("")

    lines.extend(
        [
            "## Repository knowledge",
            "",
            "- [Documentation map](knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    output_path = REPO_ROOT / "docs" / "tool-reference.md"
    output_path.write_text(render_tool_reference(), encoding="utf-8")


if __name__ == "__main__":
    main()
