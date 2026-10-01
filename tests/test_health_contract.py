from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import health_dispatch
from scripts.google_oauth_helper import PROFILE_SERVICES, _scopes_for_profile


class _Credentials:
    def __init__(self, scopes: list[str]):
        self.scopes = scopes
        self.granted_scopes = None


class _Store:
    def __init__(self, scopes: list[str]):
        self.credentials = _Credentials(scopes)
        self.requests: list[str] = []

    def get(self, email: str):
        self.requests.append(email)
        return self.credentials


class HealthContractTests(unittest.TestCase):
    def test_catalog_covers_all_documented_data_types_and_registered_tools(self):
        catalog = health_dispatch.HEALTH_CATALOG
        self.assertEqual(len(catalog), 43)
        self.assertIn("active-energy-burned", catalog)
        self.assertIn("nutrition-log", catalog)
        self.assertIn("exercise", catalog)
        self.assertIn("electrocardiogram", catalog)
        self.assertIn("menstrual-period", catalog)
        self.assertIn("total-calories", catalog)
        manifest = json.loads(Path("tool_manifest_google_health.json").read_text(encoding="utf-8"))
        self.assertEqual({tool["name"] for tool in manifest["tools"]}, health_dispatch.HEALTH_TOOL_NAMES)
        self.assertTrue(all(set(row["operations"]) and row["scopes"] for row in catalog.values()))

    def test_health_profiles_are_separate_from_workspace_scopes(self):
        workspace = _scopes_for_profile("workspace", [])
        self.assertFalse(any("googlehealth." in scope for scope in workspace))
        read = _scopes_for_profile("health-read", [])
        self.assertTrue(read)
        self.assertFalse(any(scope.endswith(".writeonly") for scope in read))
        full = _scopes_for_profile("health", [])
        self.assertIn("https://www.googleapis.com/auth/googlehealth.nutrition.writeonly", full)
        self.assertIn("https://www.googleapis.com/auth/googlehealth.activity_and_fitness.writeonly", full)
        self.assertIn("health", PROFILE_SERVICES)

    def test_nutrition_calories_and_exercise_use_distinct_write_scopes(self):
        scopes = _scopes_for_profile("health", [])
        store = _Store(scopes)
        nutrition = {"nutritionLog": {"interval": {"startTime": "2026-09-29T12:00:00Z", "endTime": "2026-09-29T12:01:00Z"}, "foodDisplayName": "Lunch", "energy": {"kcal": 600}}}
        exercise = {"exercise": {"interval": {"startTime": "2026-09-29T08:00:00Z", "endTime": "2026-09-29T08:30:00Z"}, "exerciseType": "RUNNING", "metricsSummary": {"caloriesKcal": 250}}}
        with patch.object(health_dispatch, "_request", return_value={"done": True}) as request:
            health_dispatch.dispatch_health(store, "person@example.com", "health_create_data_point", {"data_type": "nutrition-log", "body": nutrition})
            self.assertEqual(request.call_args.args[2], "users/me/dataTypes/nutrition-log/dataPoints")
            self.assertEqual(request.call_args.kwargs["body"], nutrition)
            health_dispatch.dispatch_health(store, "person@example.com", "health_create_data_point", {"data_type": "exercise", "body": exercise})
            self.assertEqual(request.call_args.args[2], "users/me/dataTypes/exercise/dataPoints")
        self.assertEqual(store.requests, ["person@example.com", "person@example.com"])

    def test_catalog_rejects_unsupported_calorie_burn_write_and_cross_type_body(self):
        store = _Store(_scopes_for_profile("health", []))
        with patch.object(health_dispatch, "_request") as request:
            with self.assertRaisesRegex(ValueError, "not supported"):
                health_dispatch.dispatch_health(store, "a@example.com", "health_create_data_point", {"data_type": "active-energy-burned", "body": {"activeEnergyBurned": {"kcal": 100}}})
            with self.assertRaisesRegex(ValueError, "nutritionLog"):
                health_dispatch.dispatch_health(store, "a@example.com", "health_create_data_point", {"data_type": "nutrition-log", "body": {"exercise": {}}})
            request.assert_not_called()

    def test_missing_scope_and_credentials_fail_before_network(self):
        store = _Store(["https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly"])
        with patch.object(health_dispatch, "_request") as request:
            with self.assertRaisesRegex(PermissionError, "nutrition.writeonly"):
                health_dispatch.dispatch_health(store, "a@example.com", "health_create_data_point", {"data_type": "nutrition-log", "body": {"nutritionLog": {}}})
            with self.assertRaisesRegex(PermissionError, "user_google_email"):
                health_dispatch.dispatch_health(store, "", "health_list_data_points", {"data_type": "steps"})
            request.assert_not_called()

    def test_read_pagination_and_self_source_filter(self):
        store = _Store(_scopes_for_profile("health-read", []))
        with patch.object(health_dispatch, "_request", return_value={"dataPoints": [], "nextPageToken": "next"}) as request:
            result = health_dispatch.dispatch_health(store, "a@example.com", "health_list_data_points", {"data_type": "steps", "filter": 'steps.interval.civil_start_time >= "2026-09-29"', "page_size": 50, "page_token": "prior", "data_source_family": "self-sources"})
        self.assertEqual(result["nextPageToken"], "next")
        self.assertEqual(request.call_args.kwargs["params"]["pageToken"], "prior")
        self.assertEqual(request.call_args.kwargs["params"]["dataSourceFamily"], "users/me/dataSourceFamilies/self-sources")
        with self.assertRaisesRegex(ValueError, "between 1 and 25"):
            health_dispatch.dispatch_health(store, "a@example.com", "health_list_data_points", {"data_type": "exercise", "page_size": 26})

    def test_resource_ids_and_batch_delete_stay_inside_selected_type(self):
        store = _Store(_scopes_for_profile("health", []))
        with patch.object(health_dispatch, "_request", return_value={"done": True}) as request:
            health_dispatch.dispatch_health(store, "a@example.com", "health_delete_data_points", {"data_type": "nutrition-log", "point_ids": ["meal-1", "meal-2"]})
            self.assertEqual(request.call_args.kwargs["body"]["names"], ["users/me/dataTypes/nutrition-log/dataPoints/meal-1", "users/me/dataTypes/nutrition-log/dataPoints/meal-2"])
            with self.assertRaisesRegex(ValueError, "invalid data point ID"):
                health_dispatch.dispatch_health(store, "a@example.com", "health_delete_data_points", {"data_type": "nutrition-log", "point_ids": ["../exercise/1"]})

    def test_user_profile_and_settings_are_scope_gated(self):
        store = _Store(_scopes_for_profile("health", []))
        with patch.object(health_dispatch, "_request", return_value={}) as request:
            health_dispatch.dispatch_health(store, "a@example.com", "health_get_profile", {})
            self.assertEqual(request.call_args.args[2], "users/me/profile")
            health_dispatch.dispatch_health(store, "a@example.com", "health_update_settings", {"body": {"name": "users/me/settings"}, "update_mask": "name"})
            self.assertEqual(request.call_args.args[1], "PATCH")
            self.assertEqual(request.call_args.kwargs["params"], {"updateMask": "name"})

    def test_http_boundary_retries_reads_only_and_redacts_error_body(self):
        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def mount(self, _url, adapter):
                self.adapter = adapter

            def request(self, method, url, **kwargs):
                self.method = method
                self.url = url
                self.kwargs = kwargs
                return SimpleNamespace(status_code=403, content=b'{"error":{"status":"MISSING_OAUTH_SCOPE","message":"private data"}}', json=lambda: {"error": {"status": "MISSING_OAUTH_SCOPE", "message": "private data"}})

        session = Session()
        with patch.object(health_dispatch, "AuthorizedSession", return_value=session):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403 \\(MISSING_OAUTH_SCOPE\\)") as failure:
                health_dispatch._request(object(), "POST", "users/me/dataTypes/exercise/dataPoints", body={"exercise": {}})
        self.assertNotIn("private data", str(failure.exception))
        self.assertEqual(session.url, "https://health.googleapis.com/v4/users/me/dataTypes/exercise/dataPoints")
        self.assertEqual(session.kwargs["timeout"], 30)
        self.assertEqual(session.adapter.max_retries.allowed_methods, {"GET"})


if __name__ == "__main__":
    unittest.main()
