"""
Google Chat MCP Tools

This module provides MCP tools for interacting with Google Chat API.
"""

import logging
import asyncio
from typing import Optional, List

from googleapiclient.errors import HttpError

# Auth & server utilities
from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@require_google_service("chat", "chat_read")
@handle_http_errors("list_spaces", service_type="chat")
async def list_spaces(
    service,
    user_google_email: str,
    page_size: int = 100,
    space_type: str = "all",  # "all", "room", "dm"
) -> str:
    """
    Lists Google Chat spaces (rooms and direct messages) accessible to the user.

    Args:
        user_google_email (str): The user's Google email address. Required.
        page_size (int): Maximum number of spaces to return.
        space_type (str): Filter by space type ("all", "room", "dm").

    Returns:
        str: A formatted list of Google Chat spaces accessible to the user.
    """
    logger.info(f"[list_spaces] Email={user_google_email}, Type={space_type}")

    # Build filter based on space_type
    filter_param = None
    if space_type == "room":
        filter_param = "spaceType = SPACE"
    elif space_type == "dm":
        filter_param = "spaceType = DIRECT_MESSAGE"

    request_params = {"pageSize": page_size}
    if filter_param:
        request_params["filter"] = filter_param

    response = await asyncio.to_thread(service.spaces().list(**request_params).execute)

    spaces = response.get("spaces", [])
    if not spaces:
        return f"No Chat spaces found for type '{space_type}'."

    output = [f"Found {len(spaces)} Chat spaces (type: {space_type}):"]
    for space in spaces:
        space_name = space.get("displayName", "Unnamed Space")
        space_id = space.get("name", "")
        space_type_actual = space.get("spaceType", "UNKNOWN")
        output.append(f"- {space_name} (ID: {space_id}, Type: {space_type_actual})")

    return "\n".join(output)


@server.tool()
@require_google_service("chat", "chat_write")
@handle_http_errors("create_space", service_type="chat")
async def create_space(
    service,
    user_google_email: str,
    display_name: str,
    space_type: str = "SPACE",
    external_user_allowed: bool = False,
) -> str:
    """
    Create a new Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        display_name (str): The display name of the space.
        space_type (str): The type of space ("SPACE" or "GROUP_CHAT"). Defaults to "SPACE".
        external_user_allowed (bool): Whether external users can join. Defaults to False.

    Returns:
        str: Confirmation message with the new space ID.
    """
    logger.info(
        f"[create_space] Invoked. Email: '{user_google_email}', Name: '{display_name}'"
    )

    body = {
        "displayName": display_name,
        "spaceType": space_type,
        "externalUserAllowed": external_user_allowed,
    }

    result = await asyncio.to_thread(service.spaces().create(body=body).execute)

    space_name = result.get("name")
    space_display_name = result.get("displayName")

    confirmation_message = f"""Space Created for {user_google_email}:
- Display Name: {space_display_name}
- Space ID: {space_name}
- Type: {space_type}
- External Allowed: {external_user_allowed}"""

    logger.info(f"Space created successfully for {user_google_email}. ID: {space_name}")
    return confirmation_message


@server.tool()
@require_google_service("chat", "chat_read")
@handle_http_errors("list_members", service_type="chat")
async def list_members(
    service,
    user_google_email: str,
    space_id: str,
    page_size: int = 100,
) -> str:
    """
    List members of a Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        space_id (str): The ID of the space (e.g., "spaces/AAAAAAAAAAA").
        page_size (int): Maximum number of members to return.

    Returns:
        str: List of members in the space.
    """
    logger.info(
        f"[list_members] Invoked. Email: '{user_google_email}', Space: '{space_id}'"
    )

    response = await asyncio.to_thread(
        service.spaces().members().list(parent=space_id, pageSize=page_size).execute
    )

    members = response.get("memberships", [])
    if not members:
        return f"No members found in space {space_id}."

    output = [f"Members in space {space_id}:"]
    for membership in members:
        member = membership.get("member", {})
        display_name = member.get("displayName", "Unknown")
        name_id = member.get("name", "Unknown")
        type_ = member.get("type", "Unknown")
        role = membership.get("role", "Unknown")
        output.append(f"- {display_name} ({type_}) - Role: {role} (ID: {name_id})")

    return "\n".join(output)


@server.tool()
@require_google_service("chat", "chat_write")
@handle_http_errors("add_member", service_type="chat")
async def add_member(
    service,
    user_google_email: str,
    space_id: str,
    member_name: str,
) -> str:
    """
    Add a member to a Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        space_id (str): The ID of the space.
        member_name (str): The resource name of the member to add (e.g., "users/123456789" or "users/user@example.com").

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[add_member] Invoked. Email: '{user_google_email}', Space: '{space_id}', Member: '{member_name}'"
    )

    body = {"member": {"name": member_name}}

    result = await asyncio.to_thread(
        service.spaces().members().create(parent=space_id, body=body).execute
    )

    member_display_name = result.get("member", {}).get("displayName", member_name)

    confirmation_message = f"Successfully added {member_display_name} to space {space_id} for {user_google_email}."
    logger.info(f"Member added successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@require_google_service("chat", "chat_write")
@handle_http_errors("remove_member", service_type="chat")
async def remove_member(
    service,
    user_google_email: str,
    space_id: str,
    member_name: str,
) -> str:
    """
    Remove a member from a Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        space_id (str): The ID of the space.
        member_name (str): The resource name of the membership to delete (e.g., "spaces/SPACE/members/MEMBER").
                           Note: This usually requires listing members first to get the membership name.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[remove_member] Invoked. Email: '{user_google_email}', Space: '{space_id}', Member: '{member_name}'"
    )

    # Note: The API expects the resource name of the membership, not just the user ID.
    # It usually looks like "spaces/{space}/members/{member}"
    if not member_name.startswith(f"{space_id}/members/"):
        # Try to construct it if only member ID is given? No, member ID is part of it.
        # Just warn or assume the user provided the correct membership name.
        pass

    await asyncio.to_thread(service.spaces().members().delete(name=member_name).execute)

    confirmation_message = f"Successfully removed {member_name} from space {space_id} for {user_google_email}."
    logger.info(f"Member removed successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@require_google_service("chat", "chat_read")
@handle_http_errors("get_messages", service_type="chat")
async def get_messages(
    service,
    user_google_email: str,
    space_id: str,
    page_size: int = 50,
    order_by: str = "createTime desc",
) -> str:
    """
    Retrieves messages from a Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        space_id (str): The ID of the space.
        page_size (int): Number of messages to retrieve.
        order_by (str): Sorting order (e.g., "createTime desc").

    Returns:
        str: Formatted messages from the specified space.
    """
    logger.info(f"[get_messages] Space ID: '{space_id}' for user '{user_google_email}'")

    # Get space info first
    space_info = await asyncio.to_thread(service.spaces().get(name=space_id).execute)
    space_name = space_info.get("displayName", "Unknown Space")

    # Get messages
    response = await asyncio.to_thread(
        service.spaces()
        .messages()
        .list(parent=space_id, pageSize=page_size, orderBy=order_by)
        .execute
    )

    messages = response.get("messages", [])
    if not messages:
        return f"No messages found in space '{space_name}' (ID: {space_id})."

    output = [f"Messages from '{space_name}' (ID: {space_id}):\n"]
    for msg in messages:
        sender = msg.get("sender", {}).get("displayName", "Unknown Sender")
        create_time = msg.get("createTime", "Unknown Time")
        text_content = msg.get("text", "No text content")
        msg_name = msg.get("name", "")

        output.append(f"[{create_time}] {sender}:")
        output.append(f"  {text_content}")
        output.append(f"  (Message ID: {msg_name})\n")

    return "\n".join(output)


@server.tool()
@require_google_service("chat", "chat_write")
@handle_http_errors("send_message", service_type="chat")
async def send_message(
    service,
    user_google_email: str,
    space_id: str,
    message_text: str,
    thread_key: Optional[str] = None,
) -> str:
    """
    Sends a message to a Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        space_id (str): The ID of the space.
        message_text (str): The text content of the message.
        thread_key (Optional[str]): A key to group messages into a thread (client-assigned).

    Returns:
        str: Confirmation message with sent message details.
    """
    logger.info(f"[send_message] Email: '{user_google_email}', Space: '{space_id}'")

    message_body = {"text": message_text}

    # Add thread key if provided (for threaded replies)
    request_params = {"parent": space_id, "body": message_body}
    if thread_key:
        request_params["threadKey"] = thread_key

    message = await asyncio.to_thread(
        service.spaces().messages().create(**request_params).execute
    )

    message_name = message.get("name", "")
    create_time = message.get("createTime", "")

    msg = f"Message sent to space '{space_id}' by {user_google_email}. Message ID: {message_name}, Time: {create_time}"
    logger.info(
        f"Successfully sent message to space '{space_id}' by {user_google_email}"
    )
    return msg


@server.tool()
@require_google_service("chat", "chat_write")
@handle_http_errors("reply_in_thread", service_type="chat")
async def reply_in_thread(
    service,
    user_google_email: str,
    space_id: str,
    thread_name: str,
    message_text: str,
) -> str:
    """
    Reply to a specific thread in a Google Chat space.

    Args:
        user_google_email (str): The user's Google email address. Required.
        space_id (str): The ID of the space.
        thread_name (str): The resource name of the thread (e.g., "spaces/SPACE/threads/THREAD").
        message_text (str): The reply text.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[reply_in_thread] Invoked. Email: '{user_google_email}', Space: '{space_id}', Thread: '{thread_name}'"
    )

    message_body = {"text": message_text, "thread": {"name": thread_name}}

    result = await asyncio.to_thread(
        service.spaces()
        .messages()
        .create(parent=space_id, body=message_body)
        .execute
    )

    message_name = result.get("name", "")
    confirmation_message = f"Reply sent to thread {thread_name} in space {space_id} for {user_google_email}. Message ID: {message_name}"
    logger.info(f"Reply sent successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@require_google_service("chat", "chat_read")
@handle_http_errors("search_messages", service_type="chat")
async def search_messages(
    service,
    user_google_email: str,
    query: str,
    space_id: Optional[str] = None,
    page_size: int = 25,
) -> str:
    """
    Searches for messages in Google Chat spaces by text content.

    Args:
        user_google_email (str): The user's Google email address. Required.
        query (str): Text to search for.
        space_id (Optional[str]): Limit search to a specific space.
        page_size (int): Max results.

    Returns:
        str: A formatted list of messages matching the search query.
    """
    logger.info(f"[search_messages] Email={user_google_email}, Query='{query}'")

    # If specific space provided, search within that space
    if space_id:
        response = await asyncio.to_thread(
            service.spaces()
            .messages()
            .list(parent=space_id, pageSize=page_size, filter=f'text:"{query}"')
            .execute
        )
        messages = response.get("messages", [])
        context = f"space '{space_id}'"
    else:
        # Search across all accessible spaces (this may require iterating through spaces)
        # For simplicity, we'll search the user's spaces first
        spaces_response = await asyncio.to_thread(
            service.spaces().list(pageSize=100).execute
        )
        spaces = spaces_response.get("spaces", [])

        messages = []
        for space in spaces[:10]:  # Limit to first 10 spaces to avoid timeout
            try:
                space_messages = await asyncio.to_thread(
                    service.spaces()
                    .messages()
                    .list(
                        parent=space.get("name"), pageSize=5, filter=f'text:"{query}"'
                    )
                    .execute
                )
                space_msgs = space_messages.get("messages", [])
                for msg in space_msgs:
                    msg["_space_name"] = space.get("displayName", "Unknown")
                messages.extend(space_msgs)
            except HttpError:
                continue  # Skip spaces we can't access
        context = "all accessible spaces"

    if not messages:
        return f"No messages found matching '{query}' in {context}."

    output = [f"Found {len(messages)} messages matching '{query}' in {context}:"]
    for msg in messages:
        sender = msg.get("sender", {}).get("displayName", "Unknown Sender")
        create_time = msg.get("createTime", "Unknown Time")
        text_content = msg.get("text", "No text content")
        space_name = msg.get("_space_name", "Unknown Space")

        # Truncate long messages
        if len(text_content) > 100:
            text_content = text_content[:100] + "..."

        output.append(f"- [{create_time}] {sender} in '{space_name}': {text_content}")

    return "\n".join(output)
