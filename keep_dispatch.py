from __future__ import annotations

from typing import Any, Callable

import requests


KEEP_TOOL_NAMES = {
    "list_keep_notes",
    "get_keep_note",
    "create_keep_note",
    "delete_keep_note",
    "download_keep_attachment",
    "share_keep_note",
    "unshare_keep_note",
    "get_keep_note_permissions",
    "find_keep_notes",
    "create_keep_list",
    "update_keep_note",
    "add_keep_list_item",
    "update_keep_list_item",
    "delete_keep_list_item",
    "set_keep_note_color",
    "pin_keep_note",
    "archive_keep_note",
    "trash_keep_note",
    "restore_keep_note",
    "list_keep_labels",
    "create_keep_label",
    "delete_keep_label",
    "add_keep_label_to_note",
    "remove_keep_label_from_note",
    "list_keep_note_collaborators",
    "add_keep_note_collaborator",
    "remove_keep_note_collaborator",
    "list_keep_note_media",
}


def dispatch_keep_master_token(
    runtime: Any,
    name: str,
    args: dict[str, Any],
    *,
    load_gkeepapi: Callable[[], Any],
    as_list: Callable[[Any, str], list[Any]],
    as_string_list: Callable[[Any, str], list[str]],
    json_export: Callable[[Any, str], dict[str, Any]],
    page_slice: Callable[[list[Any], Any, Any], tuple[list[Any], str | None]],
    keep_note_resource_name: Callable[[str], str],
) -> dict[str, Any]:
    keep_backend = runtime._keep_master_token
    user_email = args.get("user_google_email")
    if not keep_backend.configured:
        raise PermissionError("Enhanced Google Keep tools require GOOGLE_KEEP_MASTER_TOKEN and GOOGLE_KEEP_EMAIL or GOOGLE_DEFAULT_USER_EMAIL.")

    if name in {"list_keep_notes", "find_keep_notes"}:
        keep = keep_backend.client(user_email)
        query = str(args.get("query") or args.get("filter") or "").strip()
        notes = list(keep.find(query=query, labels=keep_backend.resolve_labels(keep, args.get("labels")), colors=keep_backend.normalize_colors(args.get("colors")), pinned=args.get("pinned"), archived=args.get("archived", False), trashed=args.get("trashed", False)))
        page, next_token = page_slice(notes, args.get("page_size", 25), args.get("page_token"))
        return {"notes": [keep_backend.serialize_note(note) for note in page], "nextPageToken": next_token, "estimatedTotal": len(notes)}
    if name == "get_keep_note":
        _keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        return {"note": keep_backend.serialize_note(note)}
    if name == "create_keep_note":
        keep = keep_backend.client(user_email)
        list_items = as_list(args.get("list_items"), "list_items") if isinstance(args.get("list_items"), str) else args.get("list_items")
        if args.get("text") and list_items:
            raise ValueError("Provide either text or list_items, not both")
        if list_items:
            formatted = [(str((item or {}).get("text") or ""), bool((item or {}).get("checked", False))) for item in list_items]
            note = keep.createList(title=args.get("title"), items=formatted)
        else:
            note = keep.createNote(title=args.get("title"), text=args.get("text"))
        managed_label = keep_backend.ensure_managed_label(keep)
        if managed_label is not None:
            note.labels.add(managed_label)
        keep.sync()
        return {"created": True, "note": keep_backend.serialize_note(note)}
    if name == "create_keep_list":
        keep = keep_backend.client(user_email)
        items = as_list(args.get("items"), "items") if isinstance(args.get("items"), str) else args.get("items")
        formatted_items = [(str((item or {}).get("text") or ""), bool((item or {}).get("checked", False))) for item in (items or [])]
        note = keep.createList(title=args.get("title"), items=formatted_items or None)
        managed_label = keep_backend.ensure_managed_label(keep)
        if managed_label is not None:
            note.labels.add(managed_label)
        keep.sync()
        return {"created": True, "note": keep_backend.serialize_note(note)}
    if name == "update_keep_note":
        keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        keep_backend.ensure_modifiable(note)
        if args.get("title") is not None:
            note.title = str(args.get("title") or "")
        if args.get("text") is not None:
            note.text = str(args.get("text") or "")
        keep.sync()
        return {"updated": True, "note": keep_backend.serialize_note(note)}
    if name in {"add_keep_list_item", "update_keep_list_item", "delete_keep_list_item"}:
        keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        keep_backend.ensure_modifiable(note)
        gkeepapi = load_gkeepapi()
        if not isinstance(note, gkeepapi.node.List):
            raise ValueError(f"Note {note.id} is not a checklist")
        if name == "add_keep_list_item":
            item = note.add(text=args["text"], checked=bool(args.get("checked", False)))
            keep.sync()
            return {"created": True, "item": keep_backend.serialize_list_item(item), "note": keep_backend.serialize_note(note)}
        item = note.get(args["item_id"])
        if item is None:
            raise ValueError(f"List item '{args['item_id']}' was not found")
        if name == "update_keep_list_item":
            if args.get("text") is not None:
                item.text = str(args.get("text") or "")
            if args.get("checked") is not None:
                item.checked = bool(args.get("checked"))
            keep.sync()
            return {"updated": True, "note": keep_backend.serialize_note(note)}
        item.delete()
        keep.sync()
        return {"deleted": True, "itemId": args["item_id"], "note": keep_backend.serialize_note(note)}
    if name == "set_keep_note_color":
        keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        keep_backend.ensure_modifiable(note)
        gkeepapi = load_gkeepapi()
        try:
            note.color = gkeepapi.node.ColorValue(str(args["color"]).upper())
        except ValueError as exc:
            raise ValueError(f"Invalid Keep color '{args['color']}'") from exc
        keep.sync()
        return {"updated": True, "note": keep_backend.serialize_note(note)}
    if name in {"pin_keep_note", "archive_keep_note", "trash_keep_note", "restore_keep_note", "delete_keep_note"}:
        keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        keep_backend.ensure_modifiable(note)
        if name == "pin_keep_note":
            note.pinned = bool(args.get("pinned", True))
        elif name == "archive_keep_note":
            note.archived = bool(args.get("archived", True))
        elif name == "trash_keep_note":
            note.trash()
        elif name == "restore_keep_note":
            note.untrash()
            note.undelete()
        else:
            note.delete()
        keep.sync()
        if name == "delete_keep_note":
            return {"deleted": True, "noteName": args["note_name"]}
        return {"updated": True, "note": keep_backend.serialize_note(note)}
    if name in {"list_keep_labels", "create_keep_label", "delete_keep_label"}:
        keep = keep_backend.client(user_email)
        if name == "list_keep_labels":
            return {"labels": [keep_backend.serialize_label(label) for label in keep.labels()]}
        if name == "create_keep_label":
            label = keep.createLabel(args["name"])
            keep.sync()
            return {"created": True, "label": keep_backend.serialize_label(label)}
        label = keep_backend.resolve_label(keep, args["label_id"])
        if label.name == keep_backend.managed_label_name and not keep_backend.unsafe_mode:
            raise ValueError(f"Cannot delete the managed label '{keep_backend.managed_label_name}' unless GOOGLE_KEEP_UNSAFE_MODE=true.")
        keep.deleteLabel(label.id)
        keep.sync()
        return {"deleted": True, "labelId": label.id}
    if name in {"add_keep_label_to_note", "remove_keep_label_from_note"}:
        keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        keep_backend.ensure_modifiable(note)
        label = keep_backend.resolve_label(keep, args["label_id"])
        if name == "remove_keep_label_from_note" and label.name == keep_backend.managed_label_name and not keep_backend.unsafe_mode:
            raise ValueError(f"Cannot remove the managed label '{keep_backend.managed_label_name}' unless GOOGLE_KEEP_UNSAFE_MODE=true.")
        if name == "add_keep_label_to_note":
            note.labels.add(label)
        else:
            note.labels.remove(label)
        keep.sync()
        return {"updated": True, "note": keep_backend.serialize_note(note)}
    if name in {"list_keep_note_collaborators", "share_keep_note", "add_keep_note_collaborator", "unshare_keep_note", "remove_keep_note_collaborator", "get_keep_note_permissions"}:
        keep, note = keep_backend.get_note_or_raise(user_email, args["note_name"])
        if name in {"share_keep_note", "add_keep_note_collaborator", "unshare_keep_note", "remove_keep_note_collaborator"}:
            keep_backend.ensure_modifiable(note)
        if name == "list_keep_note_collaborators":
            return {"collaborators": list(note.collaborators.all())}
        if name == "get_keep_note_permissions":
            return {"permissions": [{"email": email, "role": "WRITER"} for email in note.collaborators.all()]}
        if name == "share_keep_note":
            emails = as_string_list(args.get("writers"), "writers")
        elif name == "add_keep_note_collaborator":
            emails = [str(args["email"]).strip()]
        elif name == "unshare_keep_note":
            emails = as_string_list(args.get("emails_or_groups"), "emails_or_groups")
        else:
            emails = [str(args["email"]).strip()]
        for email in emails:
            if name in {"share_keep_note", "add_keep_note_collaborator"}:
                note.collaborators.add(email)
            else:
                note.collaborators.remove(email)
        keep.sync()
        return {"updated": True, "note": keep_backend.serialize_note(note)}
    if name == "list_keep_note_media":
        return {"media": keep_backend.list_media(user_email, args["note_name"])}
    if name == "download_keep_attachment":
        note, blob, detected_mime_type = keep_backend.find_blob(user_email, args["attachment_name"])
        media_link = keep_backend.client(user_email).getMediaLink(blob)
        response = requests.get(media_link, timeout=30)
        response.raise_for_status()
        mime_type = str(args.get("mime_type") or response.headers.get("Content-Type") or detected_mime_type or "application/octet-stream")
        return {"attachmentName": args["attachment_name"], "noteName": keep_note_resource_name(note.id), "mediaLink": media_link, **json_export(response.content, mime_type)}
    raise NotImplementedError(f"Tool '{name}' is not implemented for Google Keep master-token auth")
