from __future__ import annotations

from typing import Any, Callable


TASKS_TOOL_NAMES = {
    "list_task_lists",
    "create_task_list",
    "delete_task_list",
    "list_tasks",
    "create_task",
    "update_task",
    "delete_task",
    "complete_task",
    "reopen_task",
    "set_task_due_date",
    "clear_completed_tasks",
}


async def dispatch_tasks(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    normalize_due: Callable[[str | None], str | None],
) -> dict[str, Any]:
    svc = runtime._svc(user_email, "tasks", "v1")
    if name == "list_task_lists":
        data = svc.tasklists().list(maxResults=args.get("max_results", 100), pageToken=args.get("page_token")).execute()
        return {"taskLists": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
    if name == "create_task_list":
        return {"created": True, "taskList": svc.tasklists().insert(body={"title": args["title"]}).execute()}
    if name == "delete_task_list":
        svc.tasklists().delete(tasklist=args["task_list_id"]).execute()
        return {"deleted": True, "taskListId": args["task_list_id"]}
    if name == "list_tasks":
        data = svc.tasks().list(tasklist=args["task_list_id"], maxResults=args.get("max_results", 20), pageToken=args.get("page_token"), showCompleted=args.get("show_completed", True), showDeleted=args.get("show_deleted", False), showHidden=args.get("show_hidden", False)).execute()
        return {"tasks": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
    if name == "create_task":
        body: dict[str, Any] = {"title": args["title"]}
        if args.get("notes") is not None:
            body["notes"] = args["notes"]
        if args.get("due") is not None:
            body["due"] = normalize_due(args["due"])
        params: dict[str, Any] = {"tasklist": args["task_list_id"], "body": body}
        if args.get("parent"):
            params["parent"] = args["parent"]
        return {"created": True, "task": svc.tasks().insert(**params).execute()}
    if name == "update_task":
        body = {}
        for key in ("title", "notes", "status", "due"):
            if args.get(key) is not None:
                body[key] = normalize_due(args[key]) if key == "due" else args[key]
        return {"updated": True, "task": svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body=body).execute()}
    if name == "delete_task":
        svc.tasks().delete(tasklist=args["task_list_id"], task=args["task_id"]).execute()
        return {"deleted": True, "taskId": args["task_id"]}
    if name == "complete_task":
        data = svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body={"status": "completed"}).execute()
        return {"completed": True, "task": data}
    if name == "reopen_task":
        data = svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body={"status": "needsAction"}).execute()
        return {"updated": True, "task": data}
    if name == "set_task_due_date":
        due = normalize_due(args["due"])
        data = svc.tasks().patch(tasklist=args["task_list_id"], task=args["task_id"], body={"due": due}).execute()
        return {"updated": True, "task": data}
    if name == "clear_completed_tasks":
        svc.tasks().clear(tasklist=args["task_list_id"]).execute()
        return {"cleared": True, "taskListId": args["task_list_id"]}
    raise NotImplementedError(f"Tool '{name}' is not implemented for Tasks")
