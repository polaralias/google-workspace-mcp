from __future__ import annotations

from typing import Any, Callable


CONTACTS_TOOL_NAMES = {
    "list_contacts",
    "search_contacts",
    "create_contact",
    "update_contact",
    "delete_contact",
}


async def dispatch_contacts(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    as_string_list: Callable[[Any, str], list[str]],
    as_dict: Callable[[Any, str], dict[str, Any]],
) -> dict[str, Any]:
    svc = runtime._svc(user_email, "people", "v1")
    default_fields = "names,emailAddresses,phoneNumbers,organizations,metadata"
    if name == "list_contacts":
        params: dict[str, Any] = {"resourceName": "people/me", "personFields": args.get("person_fields", default_fields), "pageSize": args.get("page_size", 100), "pageToken": args.get("page_token")}
        if args.get("sort_order"):
            params["sortOrder"] = args["sort_order"]
        if args.get("sync_token"):
            params["syncToken"] = args["sync_token"]
        data = svc.people().connections().list(**params).execute()
        return {"contacts": data.get("connections", []), "nextPageToken": data.get("nextPageToken"), "nextSyncToken": data.get("nextSyncToken")}
    if name == "search_contacts":
        params = {"query": args["query"], "pageSize": args.get("page_size", 10), "readMask": args.get("read_mask", default_fields)}
        sources = as_string_list(args.get("sources"), "sources")
        if sources:
            params["sources"] = sources
        # The People API requires an empty-query warmup search to refresh its cache
        # before real search requests are considered current.
        svc.people().searchContacts(**{**params, "query": "", "pageSize": 1}).execute()
        data = svc.people().searchContacts(**params).execute()
        return {"results": data.get("results", [])}
    if name == "create_contact":
        person = as_dict(args.get("person"), "person")
        if not person:
            raise ValueError("person is required")
        data = svc.people().createContact(personFields=args.get("person_fields", default_fields), body=person).execute()
        return {"created": True, "person": data}
    if name == "update_contact":
        person = as_dict(args.get("person"), "person")
        if not person:
            raise ValueError("person is required")
        update_person_fields = str(args.get("update_person_fields") or ",".join(sorted(person.keys()))).strip(",")
        if not update_person_fields:
            raise ValueError("update_person_fields is required")
        person["resourceName"] = args["resource_name"]
        if not person.get("etag"):
            current = svc.people().get(resourceName=args["resource_name"], personFields=update_person_fields).execute()
            if current.get("etag"):
                person["etag"] = current["etag"]
        data = svc.people().updateContact(resourceName=args["resource_name"], updatePersonFields=update_person_fields, personFields=args.get("person_fields", default_fields), body=person).execute()
        return {"updated": True, "person": data}
    svc.people().deleteContact(resourceName=args["resource_name"]).execute()
    return {"deleted": True, "resourceName": args["resource_name"]}
