from __future__ import annotations

from typing import Any, Callable


GMAIL_TOOL_NAMES = {
    "search_gmail_messages",
    "get_gmail_message_content",
    "get_gmail_messages_content_batch",
    "get_gmail_attachment_content",
    "archive_gmail_message",
    "trash_gmail_message",
    "mark_gmail_read_unread",
    "star_unstar_gmail_message",
    "list_gmail_filters",
    "create_gmail_filter",
    "delete_gmail_filter",
}


async def dispatch_gmail(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    extract_bodies: Callable[[dict[str, Any]], tuple[str, str]],
    extract_headers: Callable[[list[dict[str, Any]] | None, list[str]], dict[str, str]],
    as_dict: Callable[[Any, str], dict[str, Any]],
) -> dict[str, Any]:
    svc = runtime._svc(user_email, "gmail", "v1")
    if name == "search_gmail_messages":
        data = svc.users().messages().list(userId="me", q=args["query"], maxResults=args.get("page_size", 10), pageToken=args.get("page_token")).execute()
        return {"messages": data.get("messages", []), "nextPageToken": data.get("nextPageToken")}
    if name == "get_gmail_message_content":
        msg = svc.users().messages().get(userId="me", id=args["message_id"], format="full").execute()
        payload = msg.get("payload") or {}
        text_body, html_body = extract_bodies(payload)
        return {"message": msg, "headers": extract_headers(payload.get("headers"), ["Subject", "From", "To", "Cc", "Message-ID", "Date"]), "body": text_body or html_body, "textBody": text_body, "htmlBody": html_body}
    if name == "get_gmail_messages_content_batch":
        fmt = args.get("format", "full")
        out: list[dict[str, Any]] = []
        for message_id in (args.get("message_ids") or [])[:25]:
            try:
                msg = svc.users().messages().get(userId="me", id=message_id, format="metadata" if fmt == "metadata" else "full", metadataHeaders=["Subject", "From", "To", "Cc", "Message-ID", "Date"]).execute()
                payload = msg.get("payload") or {}
                item: dict[str, Any] = {"messageId": message_id, "headers": extract_headers(payload.get("headers"), ["Subject", "From", "Date"]), "message": msg}
                if fmt != "metadata":
                    text_body, html_body = extract_bodies(payload)
                    item["body"] = text_body or html_body
                out.append(item)
            except Exception as exc:
                out.append({"messageId": message_id, "error": str(exc)})
        return {"results": out}
    if name == "get_gmail_attachment_content":
        data = svc.users().messages().attachments().get(userId="me", messageId=args["message_id"], id=args["attachment_id"]).execute()
        return {"attachment": data}
    if name == "archive_gmail_message":
        data = svc.users().messages().modify(userId="me", id=args["message_id"], body={"removeLabelIds": ["INBOX"]}).execute()
        return {"archived": True, "message": data}
    if name == "trash_gmail_message":
        data = svc.users().messages().trash(userId="me", id=args["message_id"]).execute()
        return {"trashed": True, "message": data}
    if name == "mark_gmail_read_unread":
        mark_read = bool(args.get("mark_read", True))
        body = {"removeLabelIds": ["UNREAD"]} if mark_read else {"addLabelIds": ["UNREAD"]}
        data = svc.users().messages().modify(userId="me", id=args["message_id"], body=body).execute()
        return {"updated": True, "markRead": mark_read, "message": data}
    if name == "star_unstar_gmail_message":
        starred = bool(args.get("starred", True))
        body = {"addLabelIds": ["STARRED"]} if starred else {"removeLabelIds": ["STARRED"]}
        data = svc.users().messages().modify(userId="me", id=args["message_id"], body=body).execute()
        return {"updated": True, "starred": starred, "message": data}
    if name == "list_gmail_filters":
        data = svc.users().settings().filters().list(userId="me").execute()
        return {"filters": data.get("filter", [])}
    if name == "create_gmail_filter":
        criteria = as_dict(args.get("criteria"), "criteria")
        action = as_dict(args.get("action"), "action")
        if not criteria or not action:
            raise ValueError("criteria and action are required")
        data = svc.users().settings().filters().create(userId="me", body={"criteria": criteria, "action": action}).execute()
        return {"created": True, "filter": data}
    if name == "delete_gmail_filter":
        svc.users().settings().filters().delete(userId="me", id=args["filter_id"]).execute()
        return {"deleted": True, "filterId": args["filter_id"]}
    raise NotImplementedError(f"Tool '{name}' is not implemented for Gmail")
