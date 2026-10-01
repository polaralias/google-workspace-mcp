"""Refresh the reviewed Google Health data-type allowlist from Google's public docs.

Run with: uv run --with beautifulsoup4 python scripts/update_health_catalog.py
Review the resulting diff against the Health API reference before publishing it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://developers.google.com/health/data-types"
DISCOVERY = "https://health.googleapis.com/$discovery/rest?version=v4"
OPERATIONS = {
    "list", "get", "reconcile", "create", "update", "batchDelete",
    "rollup", "dailyRollup", "exportExerciseTcx",
}


def main() -> None:
    response = requests.get(SOURCE, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = next(
        (
            table for table in soup.find_all("table")
            if [cell.get_text(" ", strip=True) for cell in table.find_all("th")[:3]]
            == ["Data type", "Available operations", "Scope"]
        ),
        None,
    )
    if table is None:
        raise RuntimeError("Google Health data-type table not found")

    discovery_response = requests.get(DISCOVERY, timeout=20)
    discovery_response.raise_for_status()
    discovery = discovery_response.json()
    fields = set(discovery["schemas"]["DataPoint"]["properties"])

    catalog: dict[str, dict[str, object]] = {}
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) != 3:
            continue
        detail = cells[0].get_text(" ", strip=True)
        data_type_match = re.search(r"dataType:\s*([a-z][a-z0-9-]+)", detail)
        filter_match = re.search(r"filter parameter:\s*([a-z][a-z0-9_]*)", detail)
        if not data_type_match or not filter_match:
            raise RuntimeError(f"Cannot parse data type: {detail[:100]}")
        data_type = data_type_match.group(1)
        field = re.sub(r"-([a-z])", lambda match: match.group(1).upper(), data_type)
        operations = [part.strip() for part in cells[1].get_text(" ", strip=True).split(",")]
        if not operations or not set(operations) <= OPERATIONS:
            raise RuntimeError(f"Unexpected operations for {data_type}: {operations}")
        if field not in fields and set(operations) & {"create", "update"}:
            raise RuntimeError(f"Writable type lacks a DataPoint schema field: {data_type}")
        scope_names = re.findall(r"\.[a-z_]+\.(?:readonly|writeonly)", cells[2].get_text(" ", strip=True))
        scopes = ["https://www.googleapis.com/auth/googlehealth" + scope for scope in scope_names]
        if not scopes:
            raise RuntimeError(f"Missing scopes for {data_type}")
        catalog[data_type] = {
            "field": field if field in fields else None,
            "filter": filter_match.group(1),
            "operations": operations,
            "scopes": scopes,
        }
    if len(catalog) < 35:
        raise RuntimeError(f"Unexpectedly small Health catalog: {len(catalog)}")
    output = {"source": SOURCE, "discovery": DISCOVERY, "data_types": dict(sorted(catalog.items()))}
    target = ROOT / "health_catalog.json"
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog)} data types to {target}")


if __name__ == "__main__":
    main()
