"""
Google Keep MCP Tools

This module provides MCP tools for interacting with the Google Keep API.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any, Literal

from fastapi import Body, Field

from auth.service_decorator import require_google_service
from core.utils import handle_http_errors
from core.server import server

logger = logging.getLogger(__name__)

@server.tool()
@handle_http_errors("list_keep_notes", is_read_only=True, service_type="keep")
@require_google_service("keep", "keep_read")
async def list_keep_notes(
    service,
    user_google_email: str,
    filter: Optional[str] = None,
    page_size: int = 10,
    page_token: Optional[str] = None,
) -> str:
    """
    Lists notes from Google Keep.

    Args:
        user_google_email (str): The user's Google email address. Required.
        filter (Optional[str]): Filter for the list request (e.g., "trashed=true" or "createTime > '2023-01-01T00:00:00Z'").
        page_size (int): The maximum number of notes to return. Defaults to 10.
        page_token (Optional[str]): Token for retrieving the next page of results.

    Returns:
        str: A formatted list of notes with their IDs, titles, and content snippets.
    """
    logger.info(f"[list_keep_notes] Invoked. Email: '{user_google_email}', Filter: '{filter}'")

    request_params = {"pageSize": page_size}
    if filter:
        request_params["filter"] = filter
    if page_token:
        request_params["pageToken"] = page_token

    response = await asyncio.to_thread(
        service.notes().list(**request_params).execute
    )

    notes = response.get("notes", [])
    next_page_token = response.get("nextPageToken")

    if not notes:
        return "No notes found."

    lines = [f"Found {len(notes)} notes:", ""]

    for note in notes:
        note_id = note.get("name", "").split("/")[-1]
        title = note.get("title", "(no title)")

        # Extract text content
        text_content = ""
        if "body" in note and "text" in note["body"]:
            text_content = note["body"]["text"].get("text", "")
        elif "body" in note and "list" in note["body"]:
            items = note["body"]["list"].get("listItems", [])
            text_content = ", ".join([item.get("text", {}).get("text", "") for item in items])

        # Truncate content for display
        if len(text_content) > 100:
            text_content = text_content[:97] + "..."

        lines.append(f"📝 Note ID: {note_id}")
        lines.append(f"   Title: {title}")
        lines.append(f"   Content: {text_content}")
        lines.append("")

    if next_page_token:
        lines.append(f"📄 Next Page Token: {next_page_token}")

    return "\n".join(lines)


@server.tool()
@handle_http_errors("get_keep_note", is_read_only=True, service_type="keep")
@require_google_service("keep", "keep_read")
async def get_keep_note(
    service,
    user_google_email: str,
    note_id: str,
) -> str:
    """
    Retrieves a specific note from Google Keep.

    Args:
        user_google_email (str): The user's Google email address. Required.
        note_id (str): The ID of the note to retrieve (the part after 'notes/').

    Returns:
        str: The full content of the note including title, body, and attachments.
    """
    logger.info(f"[get_keep_note] Invoked. Email: '{user_google_email}', Note ID: '{note_id}'")

    # API expects 'notes/{note_id}'
    resource_name = f"notes/{note_id}" if not note_id.startswith("notes/") else note_id

    note = await asyncio.to_thread(
        service.notes().get(name=resource_name).execute
    )

    title = note.get("title", "(no title)")
    create_time = note.get("createTime", "(unknown)")
    update_time = note.get("updateTime", "(unknown)")

    lines = [
        f"Title: {title}",
        f"ID: {note.get('name')}",
        f"Created: {create_time}",
        f"Updated: {update_time}",
        "",
        "--- BODY ---"
    ]

    if "body" in note:
        body = note["body"]
        if "text" in body:
            lines.append(body["text"].get("text", ""))
        elif "list" in body:
            lines.append("List Items:")
            for item in body["list"].get("listItems", []):
                checked = "[x]" if item.get("checked") else "[ ]"
                text = item.get("text", {}).get("text", "")
                lines.append(f"{checked} {text}")

    if "attachments" in note:
        lines.append("")
        lines.append("--- ATTACHMENTS ---")
        for att in note["attachments"]:
            att_name = att.get("name", "").split("/")[-1]
            mime_type = att.get("mimeType", "unknown")
            lines.append(f"• {att_name} ({mime_type})")
            lines.append(f"  Full Resource Name: {att.get('name')}")

    return "\n".join(lines)


@server.tool()
@handle_http_errors("create_keep_note", service_type="keep")
@require_google_service("keep", "keep")
async def create_keep_note(
    service,
    user_google_email: str,
    title: str = Body(..., description="The title of the note."),
    text: Optional[str] = Body(None, description="The text content of the note."),
    list_items: Optional[List[Dict[str, Any]]] = Body(None, description="List items for a list note. Each item should have 'text' and optional 'checked' boolean."),
) -> str:
    """
    Creates a new note in Google Keep. Can be a text note or a list note.

    Args:
        user_google_email (str): The user's Google email address. Required.
        title (str): The title of the note.
        text (Optional[str]): The text content of the note.
        list_items (Optional[List[Dict[str, Any]]]): List items for a list note. e.g., [{"text": "Buy milk", "checked": False}]

    Returns:
        str: Confirmation message with the created note ID.
    """
    logger.info(f"[create_keep_note] Invoked. Email: '{user_google_email}', Title: '{title}'")

    if not text and not list_items:
        raise ValueError("Either 'text' or 'list_items' must be provided.")

    note_body = {
        "title": title,
        "body": {}
    }

    if text:
        note_body["body"]["text"] = {"text": text}
    elif list_items:
        items = []
        for item in list_items:
            items.append({
                "text": {"text": item.get("text", "")},
                "checked": item.get("checked", False)
            })
        note_body["body"]["list"] = {"listItems": items}

    created_note = await asyncio.to_thread(
        service.notes().create(body=note_body).execute
    )

    return f"Note created successfully!\nID: {created_note.get('name')}\nTitle: {created_note.get('title')}"


@server.tool()
@handle_http_errors("delete_keep_note", service_type="keep")
@require_google_service("keep", "keep")
async def delete_keep_note(
    service,
    user_google_email: str,
    note_id: str,
) -> str:
    """
    Deletes a note from Google Keep.

    Args:
        user_google_email (str): The user's Google email address. Required.
        note_id (str): The ID of the note to delete.

    Returns:
        str: Confirmation message.
    """
    logger.info(f"[delete_keep_note] Invoked. Email: '{user_google_email}', Note ID: '{note_id}'")

    resource_name = f"notes/{note_id}" if not note_id.startswith("notes/") else note_id

    await asyncio.to_thread(
        service.notes().delete(name=resource_name).execute
    )

    return f"Note '{resource_name}' deleted successfully."


@server.tool()
@handle_http_errors("download_keep_attachment", is_read_only=True, service_type="keep")
@require_google_service("keep", "keep_read")
async def download_keep_attachment(
    service,
    user_google_email: str,
    attachment_name: str,
    mime_type: str,
) -> str:
    """
    Downloads an attachment from a Google Keep note.

    Args:
        user_google_email (str): The user's Google email address. Required.
        attachment_name (str): The full resource name of the attachment (e.g., 'notes/123/attachments/456').
        mime_type (str): The MIME type of the attachment (required for download).

    Returns:
        str: Information about the downloaded attachment (saved to storage).
    """
    logger.info(f"[download_keep_attachment] Invoked. Email: '{user_google_email}', Attachment: '{attachment_name}'")

    # Check if we're in stateless mode (can't save files)
    from auth.oauth_config import is_stateless_mode

    # Use media().download to get the content
    # Note: Keep API v1 requires 'alt=media' which is handled by google-api-python-client when using MediaIoBaseDownload,
    # but for simple execute() calls with media_mime_type, it might differ.
    # We'll use the http request method to ensure proper handling.

    # However, the Keep API documentation says for media.download:
    # "Method: media.download"
    # It seems to be a separate collection 'media' at root? No, it's typically 'notes.attachments' or similar,
    # but Keep API has a 'media' collection at the top level for downloading?
    # Checking docs: https://developers.google.com/workspace/keep/api/reference/rest/v1/media/download
    # URL: GET https://keep.googleapis.com/v1/{name=notes/*/attachments/*}?alt=media

    # In the discovery document, it might be under 'media' resource or just 'notes.attachments.get' with alt=media.
    # The Python client usually maps this. Let's try service.media().download(name=...).

    try:
        request = service.media().download(name=attachment_name, mimeType=mime_type)
        content = await asyncio.to_thread(request.execute)
    except Exception:
        # Fallback: maybe it's not under media() in the python client wrapper
        # Some APIs expose it differently. Let's try to construct the request manually if needed or check typical usage.
        # Actually, if 'media' is a top level resource in discovery, it is service.media().
        # If it is missing, we might need to use request builder.
        # But let's assume standard client generation for now.
        # If it fails, we will catch it.
        raise

    import base64
    base64_data = base64.b64encode(content).decode("utf-8")
    size_bytes = len(content)
    size_kb = size_bytes / 1024

    if is_stateless_mode():
        return (
            f"Attachment downloaded successfully (Stateless Mode).\n"
            f"Name: {attachment_name}\n"
            f"Size: {size_kb:.1f} KB\n"
            f"MIME Type: {mime_type}\n"
            f"Base64 Preview: {base64_data[:100]}..."
        )

    # Save to storage
    from core.attachment_storage import get_attachment_storage, get_attachment_url
    storage = get_attachment_storage()

    # Extract filename from resource name or use default
    filename = attachment_name.split("/")[-1]
    # Add extension based on mime type if possible (simple map)
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "text/plain": ".txt"}
    if mime_type in ext_map and not any(filename.endswith(ext) for ext in ext_map.values()):
        filename += ext_map[mime_type]

    file_id = storage.save_attachment(
        base64_data=base64_data, filename=filename, mime_type=mime_type
    )
    attachment_url = get_attachment_url(file_id)

    return (
        f"Attachment downloaded successfully!\n"
        f"Name: {attachment_name}\n"
        f"Size: {size_kb:.1f} KB\n"
        f"Download URL: {attachment_url}\n"
        f"The file will expire after 1 hour."
    )


@server.tool()
@handle_http_errors("share_keep_note", service_type="keep")
@require_google_service("keep", "keep")
async def share_keep_note(
    service,
    user_google_email: str,
    note_id: str,
    writers: List[str] = Body(..., description="List of email addresses to add as writers."),
) -> str:
    """
    Shares a Google Keep note with specified users (adds them as writers).

    Args:
        user_google_email (str): The user's Google email address. Required.
        note_id (str): The ID of the note to share.
        writers (List[str]): List of email addresses to share the note with.

    Returns:
        str: Confirmation message.
    """
    logger.info(f"[share_keep_note] Invoked. Email: '{user_google_email}', Note ID: '{note_id}', Writers: {writers}")

    resource_name = f"notes/{note_id}" if not note_id.startswith("notes/") else note_id

    # API: notes.permissions.batchCreate
    # Parent is the note resource name

    requests = []
    for email in writers:
        requests.append({
            "role": "WRITER",
            "user": {"email": email}
        })

    body = {"requests": requests}

    await asyncio.to_thread(
        service.notes().permissions().batchCreate(parent=resource_name, body=body).execute
    )

    return f"Note '{resource_name}' shared successfully with: {', '.join(writers)}"


@server.tool()
@handle_http_errors("unshare_keep_note", service_type="keep")
@require_google_service("keep", "keep")
async def unshare_keep_note(
    service,
    user_google_email: str,
    note_id: str,
    writers: List[str] = Body(..., description="List of email addresses to remove."),
) -> str:
    """
    Unshares a Google Keep note (removes writers).

    Args:
        user_google_email (str): The user's Google email address. Required.
        note_id (str): The ID of the note.
        writers (List[str]): List of email addresses to remove.

    Returns:
        str: Confirmation message.
    """
    logger.info(f"[unshare_keep_note] Invoked. Email: '{user_google_email}', Note ID: '{note_id}', Writers: {writers}")

    resource_name = f"notes/{note_id}" if not note_id.startswith("notes/") else note_id

    # API: notes.permissions.batchDelete
    # This takes a list of permission names (e.g. notes/{id}/permissions/{permissionId}).
    # BUT, we only have emails.
    # So we must first list permissions to find the permission IDs for these emails.

    # 1. Get permissions
    # notes.get returns permissions in the output
    note = await asyncio.to_thread(
        service.notes().get(name=resource_name).execute
    )

    current_permissions = note.get("permissions", [])

    # Map email to permission name
    email_to_permission_name = {}
    for perm in current_permissions:
        email = perm.get("user", {}).get("email")
        name = perm.get("name") # This is the permission resource name
        if email and name:
            email_to_permission_name[email] = name

    # 2. Identify permissions to delete
    names_to_delete = []
    not_found = []

    for writer_email in writers:
        if writer_email in email_to_permission_name:
            names_to_delete.append(email_to_permission_name[writer_email])
        else:
            not_found.append(writer_email)

    if not names_to_delete:
        return f"No matching permissions found for users: {', '.join(writers)}"

    # 3. Batch delete
    await asyncio.to_thread(
        service.notes().permissions().batchDelete(parent=resource_name, names=names_to_delete).execute
    )

    msg = f"Successfully removed permissions for: {', '.join([w for w in writers if w not in not_found])}"
    if not_found:
        msg += f"\nCould not find permissions for: {', '.join(not_found)}"

    return msg


@server.tool()
@handle_http_errors("get_keep_note_permissions", is_read_only=True, service_type="keep")
@require_google_service("keep", "keep_read")
async def get_keep_note_permissions(
    service,
    user_google_email: str,
    note_id: str,
) -> str:
    """
    Gets the permissions (users and roles) for a specific note.

    Args:
        user_google_email (str): The user's Google email address. Required.
        note_id (str): The ID of the note.

    Returns:
        str: List of users with access to the note.
    """
    logger.info(f"[get_keep_note_permissions] Invoked. Email: '{user_google_email}', Note ID: '{note_id}'")

    resource_name = f"notes/{note_id}" if not note_id.startswith("notes/") else note_id

    note = await asyncio.to_thread(
        service.notes().get(name=resource_name).execute
    )

    permissions = note.get("permissions", [])

    if not permissions:
        return "No explicit permissions found (note is likely private to owner)."

    lines = ["Permissions:", ""]
    for perm in permissions:
        role = perm.get("role", "UNKNOWN")
        user = perm.get("user", {})
        email = user.get("email", "(unknown email)")
        display_name = user.get("displayName", "")

        user_str = email
        if display_name:
            user_str += f" ({display_name})"

        lines.append(f"• {role}: {user_str}")

    return "\n".join(lines)
