"""Build the stable MCP tool schema for the Google Health API surface."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMAIL = {"type": "string", "description": "Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL."}
DATA_TYPE = {"type": "string", "description": "One of the dataType IDs returned by health_catalog."}
POINT_ID = {"type": "string", "description": "The final ID segment of a users/me/dataTypes/{data_type}/dataPoints/{point_id} resource."}
BODY = {"type": "object", "description": "Google Health API v4 request body for this operation."}


def tool(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    parameters = {"type": "object", "properties": {"user_google_email": EMAIL, **properties}, "additionalProperties": False}
    if required:
        parameters["required"] = required
    return {"name": name, "description": description, "parameters": parameters}


def main() -> None:
    tools = [
        tool("health_catalog", "List the 43 documented Google Health data types, allowed operations, and required OAuth scopes.", {}),
        tool("health_list_data_points", "List Google Health records for a documented data type. Use page_token for the next page.", {
            "data_type": DATA_TYPE, "filter": {"type": "string"}, "page_size": {"type": "integer", "default": 25},
            "page_token": {"type": "string"}, "data_source_family": {"type": "string", "enum": ["all-sources", "google-wearables", "google-sources", "self-sources"]},
        }, ["data_type"]),
        tool("health_get_data_point", "Read one Google Health record by data type and point ID.", {"data_type": DATA_TYPE, "point_id": POINT_ID}, ["data_type", "point_id"]),
        tool("health_create_data_point", "Create a Google Health record where the selected data type supports create. Use nutrition-log for calories consumed and exercise for workout sessions.", {"data_type": DATA_TYPE, "body": BODY}, ["data_type", "body"]),
        tool("health_update_data_point", "Update a Google Health record owned by the OAuth client where the data type supports update.", {"data_type": DATA_TYPE, "point_id": POINT_ID, "body": BODY}, ["data_type", "point_id", "body"]),
        tool("health_delete_data_points", "Delete 1 to 100 records of one Google Health data type owned by the OAuth client.", {"data_type": DATA_TYPE, "point_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 100}}, ["data_type", "point_ids"]),
        tool("health_reconcile_data_points", "Reconcile Google Health records where the data type supports reconciliation.", {"data_type": DATA_TYPE, "filter": {"type": "string"}, "data_source_family": {"type": "string", "enum": ["all-sources", "google-wearables", "google-sources", "self-sources"]}}, ["data_type"]),
        tool("health_rollup_data_points", "Aggregate Google Health records using a v4 RollUpDataPointsRequest body.", {"data_type": DATA_TYPE, "body": BODY}, ["data_type", "body"]),
        tool("health_daily_rollup_data_points", "Aggregate Google Health records by day using a v4 DailyRollUpDataPointsRequest body.", {"data_type": DATA_TYPE, "body": BODY}, ["data_type", "body"]),
        tool("health_export_exercise_tcx", "Export one exercise record as TCX, capped at 1 MB.", {"data_type": {"type": "string", "const": "exercise"}, "point_id": POINT_ID, "partial_data": {"type": "boolean", "default": False}}, ["data_type", "point_id"]),
        tool("health_get_identity", "Read the Google Health user identity.", {}),
        tool("health_get_profile", "Read the Google Health user profile.", {}),
        tool("health_update_profile", "Update the Google Health user profile using an update mask.", {"body": BODY, "update_mask": {"type": "string"}}, ["body"]),
        tool("health_get_settings", "Read the Google Health user settings.", {}),
        tool("health_update_settings", "Update the Google Health user settings using an update mask.", {"body": BODY, "update_mask": {"type": "string"}}, ["body"]),
        tool("health_get_irn_profile", "Read the Google Health irregular rhythm notification profile.", {}),
    ]
    target = ROOT / "tool_manifest_google_health.json"
    target.write_text(json.dumps({"tools": tools}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(tools)} Google Health tools to {target}")


if __name__ == "__main__":
    main()
