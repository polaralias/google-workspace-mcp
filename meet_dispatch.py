from __future__ import annotations

from typing import Any


MEET_TOOL_NAMES = {"list_conference_records", "get_conference_record"}


async def dispatch_meet(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    svc = runtime._svc(user_email, "meet", "v2")
    if name == "list_conference_records":
        data = svc.conferenceRecords().list(pageSize=args.get("page_size", 25), pageToken=args.get("page_token"), filter=args.get("filter")).execute()
        return {"conferenceRecords": data.get("conferenceRecords", []), "nextPageToken": data.get("nextPageToken")}
    return {"conferenceRecord": svc.conferenceRecords().get(name=args["name"]).execute()}
