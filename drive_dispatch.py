from __future__ import annotations

import io
from typing import Any

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload


DRIVE_TOOL_NAMES = {
    "search_drive_files",
    "list_drive_items",
    "get_drive_file_content",
    "create_drive_file",
    "get_drive_file_permissions",
    "create_drive_folder",
    "copy_drive_file",
    "trash_drive_file",
    "untrash_drive_file",
    "delete_drive_file",
    "list_drive_revisions",
    "get_drive_revision",
    "list_shared_drives",
}


def _execute_with_transient_retry(request: Any, *, attempts: int = 3) -> Any:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return request.execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            if status not in {500, 502, 503, 504}:
                raise
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("Drive request did not execute")


def resolve_drive_item(drive: Any, file_id: str) -> tuple[str, dict[str, Any]]:
    current = file_id
    for _ in range(6):
        meta = drive.files().get(
            fileId=current,
            fields="id,mimeType,shortcutDetails(targetId,targetMimeType),name,webViewLink",
            supportsAllDrives=True,
        ).execute()
        if meta.get("mimeType") != "application/vnd.google-apps.shortcut":
            return current, meta
        target = ((meta.get("shortcutDetails") or {}).get("targetId"))
        if not target:
            break
        current = target
    raise RuntimeError(f"Unable to resolve drive item: {file_id}")


def resolve_folder(drive: Any, folder_id: str) -> str:
    resolved, meta = resolve_drive_item(drive, folder_id)
    if meta.get("mimeType") != "application/vnd.google-apps.folder":
        raise RuntimeError(f"Resolved id '{resolved}' is not a folder")
    return resolved


async def dispatch_drive(runtime: Any, user_email: str | None, name: str, args: dict[str, Any]) -> dict[str, Any]:
    svc = runtime._svc(user_email, "drive", "v3")
    if name == "search_drive_files":
        query = str(args["query"])
        if "=" not in query and "contains" not in query:
            escaped = query.replace("'", "\\'")
            query = f"fullText contains '{escaped}'"
        params: dict[str, Any] = {
            "q": query,
            "pageSize": args.get("page_size", 10),
            "pageToken": args.get("page_token"),
            "fields": "nextPageToken, files(id,name,mimeType,webViewLink,iconLink,modifiedTime,size)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": args.get("include_items_from_all_drives", True),
        }
        if args.get("drive_id"):
            params["driveId"] = args["drive_id"]
            params["corpora"] = args.get("corpora", "drive")
        elif args.get("corpora"):
            params["corpora"] = args["corpora"]
        data = svc.files().list(**params).execute()
        return {"files": data.get("files", []), "nextPageToken": data.get("nextPageToken")}
    if name == "list_drive_items":
        folder_id = runtime._resolve_folder(svc, args.get("folder_id", "root"))
        params = {
            "q": f"'{folder_id}' in parents and trashed=false",
            "pageSize": args.get("page_size", 100),
            "pageToken": args.get("page_token"),
            "fields": "nextPageToken, files(id,name,mimeType,webViewLink,iconLink,modifiedTime,size)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": args.get("include_items_from_all_drives", True),
        }
        if args.get("drive_id"):
            params["driveId"] = args["drive_id"]
            params["corpora"] = args.get("corpora", "drive")
        elif args.get("corpora"):
            params["corpora"] = args["corpora"]
        data = svc.files().list(**params).execute()
        return {"files": data.get("files", []), "nextPageToken": data.get("nextPageToken")}
    if name == "get_drive_file_content":
        file_id, meta = runtime._resolve_drive_item(svc, args["file_id"])
        mime_type = meta.get("mimeType")
        if mime_type == "application/vnd.google-apps.document":
            raw = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
            content = raw.decode("utf-8", errors="replace")
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            raw = svc.files().export(fileId=file_id, mimeType="text/csv").execute()
            content = raw.decode("utf-8", errors="replace")
        else:
            raw = svc.files().get_media(fileId=file_id).execute()
            if not isinstance(raw, bytes):
                raise RuntimeError("Drive file content request did not return media bytes")
            content = raw.decode("utf-8", errors="replace")
        return {"file": meta, "resolvedId": file_id, "content": content}
    if name == "create_drive_file":
        if not args.get("content"):
            raise ValueError("content is required")
        folder_id = runtime._resolve_folder(svc, args.get("folder_id", "root"))
        mime_type = args.get("mime_type", "text/plain")
        upload = MediaIoBaseUpload(
            io.BytesIO(str(args["content"]).encode("utf-8")),
            mimetype=mime_type,
            resumable=False,
        )
        data = svc.files().create(
            body={"name": args["file_name"], "parents": [folder_id], "mimeType": mime_type},
            media_body=upload,
            fields="id,name,webViewLink,mimeType",
            supportsAllDrives=True,
        )
        data = _execute_with_transient_retry(data)
        return {"created": True, "file": data}
    if name == "get_drive_file_permissions":
        file_id, _ = runtime._resolve_drive_item(svc, args["file_id"])
        data = svc.files().get(
            fileId=file_id,
            fields="id,name,mimeType,size,modifiedTime,permissions(id,type,role,emailAddress,domain,expirationTime),webViewLink,shared",
            supportsAllDrives=True,
        ).execute()
        return {"file": data}
    if name == "create_drive_folder":
        parent_id = runtime._resolve_folder(svc, args.get("parent_folder_id", "root"))
        data = svc.files().create(
            body={
                "name": args["folder_name"],
                "parents": [parent_id],
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id,name,webViewLink,mimeType,parents",
            supportsAllDrives=True,
        )
        data = _execute_with_transient_retry(data)
        return {"created": True, "folder": data}
    if name == "copy_drive_file":
        file_id, _ = runtime._resolve_drive_item(svc, args["file_id"])
        body: dict[str, Any] = {}
        if args.get("name"):
            body["name"] = args["name"]
        if args.get("parent_folder_id"):
            body["parents"] = [runtime._resolve_folder(svc, args["parent_folder_id"])]
        data = svc.files().copy(
            fileId=file_id,
            body=body,
            fields="id,name,webViewLink,mimeType,parents",
            supportsAllDrives=True,
        ).execute()
        return {"copied": True, "file": data}
    if name in {"trash_drive_file", "untrash_drive_file"}:
        file_id, _ = runtime._resolve_drive_item(svc, args["file_id"])
        data = svc.files().update(
            fileId=file_id,
            body={"trashed": name == "trash_drive_file"},
            fields="id,name,trashed,webViewLink",
            supportsAllDrives=True,
        ).execute()
        return {"updated": True, "trashed": data.get("trashed"), "file": data}
    if name == "delete_drive_file":
        file_id, _ = runtime._resolve_drive_item(svc, args["file_id"])
        svc.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return {"deleted": True, "fileId": file_id}
    if name == "list_drive_revisions":
        file_id, _ = runtime._resolve_drive_item(svc, args["file_id"])
        data = svc.revisions().list(
            fileId=file_id,
            pageSize=args.get("page_size", 50),
            pageToken=args.get("page_token"),
            fields="nextPageToken,revisions(id,mimeType,modifiedTime,keepForever,size,published,lastModifyingUser(displayName,emailAddress))",
        ).execute()
        return {"revisions": data.get("revisions", []), "nextPageToken": data.get("nextPageToken")}
    if name == "get_drive_revision":
        file_id, _ = runtime._resolve_drive_item(svc, args["file_id"])
        data = svc.revisions().get(
            fileId=file_id,
            revisionId=args["revision_id"],
            fields="id,mimeType,modifiedTime,keepForever,size,published,lastModifyingUser(displayName,emailAddress),exportLinks",
        ).execute()
        return {"revision": data}
    if name == "list_shared_drives":
        data = svc.drives().list(pageSize=args.get("page_size", 100), pageToken=args.get("page_token")).execute()
        return {"sharedDrives": data.get("drives", []), "nextPageToken": data.get("nextPageToken")}

    raise NotImplementedError(f"Tool '{name}' is not implemented for Drive")
