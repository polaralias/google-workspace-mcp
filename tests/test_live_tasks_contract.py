import unittest
import uuid

from tests.live_harness import live_runtime, require_live_google_workspace


class TasksLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_tasks_create_update_delete_lifecycle_uses_owned_artifact_cleanup(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            task_lists = await runtime.dispatch("list_task_lists", {})
            self.assertIsInstance(task_lists["taskLists"], list)

            marker = "codex-live-task-" + uuid.uuid4().hex[:8]
            deleted_task = False
            deleted_list = False
            task_id = None
            task_list_id = None

            async def cleanup():
                if task_id and not deleted_task:
                    await runtime.dispatch(
                        "delete_task",
                        {"task_list_id": task_list_id, "task_id": task_id},
                    )
                if task_list_id and not deleted_list:
                    await runtime.dispatch("delete_task_list", {"task_list_id": task_list_id})

            created_list = await runtime.dispatch("create_task_list", {"title": marker})
            task_list_id = created_list["taskList"]["id"]
            self.addAsyncCleanup(cleanup)

            initial = await runtime.dispatch("list_tasks", {"task_list_id": task_list_id})
            self.assertEqual(initial.get("tasks", []), [])

            created_task = await runtime.dispatch(
                "create_task",
                {"task_list_id": task_list_id, "title": marker},
            )
            task_id = created_task["task"]["id"]

            listed = await runtime.dispatch("list_tasks", {"task_list_id": task_list_id})
            listed_ids = {item["id"] for item in listed.get("tasks", [])}
            self.assertIn(task_id, listed_ids)

            updated = await runtime.dispatch(
                "update_task",
                {
                    "task_list_id": task_list_id,
                    "task_id": task_id,
                    "title": marker + "-updated",
                    "notes": "updated during live contract validation",
                },
            )
            self.assertEqual(updated["task"]["title"], marker + "-updated")

            deleted_task_result = await runtime.dispatch(
                "delete_task",
                {"task_list_id": task_list_id, "task_id": task_id},
            )
            deleted_task = True

            deleted_list_result = await runtime.dispatch(
                "delete_task_list",
                {"task_list_id": task_list_id},
            )
            deleted_list = True

        self.assertTrue(deleted_task_result["deleted"])
        self.assertTrue(deleted_list_result["deleted"])
