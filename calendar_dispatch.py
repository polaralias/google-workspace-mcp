from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


CALENDAR_TOOL_NAMES = {
    "list_calendars",
    "get_events",
    "create_event",
    "delete_event",
    "get_free_busy",
    "list_calendar_acl",
    "create_calendar_acl_rule",
    "delete_calendar_acl_rule",
    "create_recurring_event",
}


async def dispatch_calendar(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    correct_time_format: Callable[[str | None], str | None],
    build_calendar_event_body: Callable[[dict[str, Any], bool], dict[str, Any]],
    as_list: Callable[[Any, str], list[Any]],
) -> dict[str, Any]:
    svc = runtime._svc(user_email, "calendar", "v3")
    if name == "list_calendars":
        data = svc.calendarList().list(maxResults=args.get("page_size", 100), pageToken=args.get("page_token")).execute()
        return {"calendars": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
    if name == "get_events":
        calendar_id = args.get("calendar_id", "primary")
        if args.get("event_id"):
            return {"event": svc.events().get(calendarId=calendar_id, eventId=args["event_id"]).execute()}
        params: dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": args.get("page_size", 25),
            "singleEvents": True,
            "orderBy": "startTime",
            "pageToken": args.get("page_token"),
            "q": args.get("query"),
            "timeMin": correct_time_format(args.get("time_min")) or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if args.get("time_max"):
            params["timeMax"] = correct_time_format(args["time_max"])
        data = svc.events().list(**params).execute()
        return {"events": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
    if name in {"create_event", "create_recurring_event"}:
        body = build_calendar_event_body(args, name == "create_recurring_event")
        params: dict[str, Any] = {
            "calendarId": args.get("calendar_id", "primary"),
            "body": body,
            "conferenceDataVersion": 1 if args.get("add_google_meet") else 0,
        }
        if args.get("send_updates"):
            params["sendUpdates"] = args["send_updates"]
        if args.get("supports_attachments") is not None:
            params["supportsAttachments"] = bool(args["supports_attachments"])
        data = svc.events().insert(**params).execute()
        return {"created": True, "event": data}
    if name == "delete_event":
        svc.events().delete(calendarId=args.get("calendar_id", "primary"), eventId=args["event_id"]).execute()
        return {"deleted": True, "eventId": args["event_id"]}
    if name == "get_free_busy":
        items = [{"id": item} if isinstance(item, str) else item for item in (as_list(args.get("items"), "items") if isinstance(args.get("items"), str) else args.get("items") or [])]
        if not items:
            raise ValueError("items is required")
        body = {"timeMin": correct_time_format(args["time_min"]), "timeMax": correct_time_format(args["time_max"]), "items": items}
        if args.get("time_zone"):
            body["timeZone"] = args["time_zone"]
        return {"freeBusy": svc.freebusy().query(body=body).execute()}
    if name == "list_calendar_acl":
        data = svc.acl().list(
            calendarId=args.get("calendar_id", "primary"),
            maxResults=args.get("page_size", 100),
            pageToken=args.get("page_token"),
            showDeleted=args.get("show_deleted", False),
        ).execute()
        return {"rules": data.get("items", []), "nextPageToken": data.get("nextPageToken")}
    if name == "create_calendar_acl_rule":
        body = {"role": args["role"], "scope": {"type": args["scope_type"], "value": args["scope_value"]}}
        data = svc.acl().insert(
            calendarId=args.get("calendar_id", "primary"),
            body=body,
            sendNotifications=args.get("send_notifications", False),
        ).execute()
        return {"created": True, "rule": data}
    if name == "delete_calendar_acl_rule":
        svc.acl().delete(calendarId=args.get("calendar_id", "primary"), ruleId=args["rule_id"]).execute()
        return {"deleted": True, "ruleId": args["rule_id"]}
    raise NotImplementedError(f"Tool '{name}' is not implemented for Calendar")
