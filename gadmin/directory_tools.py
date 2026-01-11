"""
Google Admin SDK Directory API Tools

This module provides MCP tools for interacting with the Google Admin SDK Directory API.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from googleapiclient.errors import HttpError

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


# --- User Management Tools ---


@server.tool()
@require_google_service("admin_directory", "admin_directory_user_readonly")
@handle_http_errors("list_users", service_type="admin_directory")
async def list_users(
    service,
    user_google_email: str,
    domain: Optional[str] = None,
    query: Optional[str] = None,
    page_size: int = 100,
    page_token: Optional[str] = None,
) -> str:
    """
    List users in the domain.

    Args:
        user_google_email (str): The user's Google email address. Required.
        domain (Optional[str]): The domain name to list users from. If not provided, uses the customer's primary domain.
        query (Optional[str]): Query string for filtering users (e.g., "email:user@example.com").
        page_size (int): Maximum number of users to return. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of users.
    """
    logger.info(f"[list_users] Invoked. Email: '{user_google_email}', Domain: '{domain}'")

    params = {"customer": "my_customer", "maxResults": page_size}
    if domain:
        params["domain"] = domain
    if query:
        params["query"] = query
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(service.users().list(**params).execute)

    users = result.get("users", [])
    next_page_token = result.get("nextPageToken")

    if not users:
        return "No users found."

    output = [f"Found {len(users)} users:"]
    for user in users:
        primary_email = user.get("primaryEmail", "Unknown Email")
        name = user.get("name", {}).get("fullName", "Unknown Name")
        suspended = " (Suspended)" if user.get("suspended") else ""
        output.append(f"- {name} <{primary_email}>{suspended}")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("admin_directory", "admin_directory_user_readonly")
@handle_http_errors("get_user", service_type="admin_directory")
async def get_user(
    service,
    user_google_email: str,
    user_key: str,
) -> str:
    """
    Get details of a specific user.

    Args:
        user_google_email (str): The user's Google email address. Required.
        user_key (str): The user's primary email address or unique ID.

    Returns:
        str: User details.
    """
    logger.info(
        f"[get_user] Invoked. Email: '{user_google_email}', User Key: '{user_key}'"
    )

    user = await asyncio.to_thread(service.users().get(userKey=user_key).execute)

    name = user.get("name", {}).get("fullName", "Unknown Name")
    primary_email = user.get("primaryEmail", "Unknown Email")
    org_unit = user.get("orgUnitPath", "Unknown OU")
    suspended = user.get("suspended", False)
    creation_time = user.get("creationTime", "Unknown")
    last_login = user.get("lastLoginTime", "Never")

    result = f"""User Details for {user_key}:
- Name: {name}
- Email: {primary_email}
- Org Unit: {org_unit}
- Suspended: {suspended}
- Created: {creation_time}
- Last Login: {last_login}"""

    return result


@server.tool()
@require_google_service("admin_directory", "admin_directory_user")
@handle_http_errors("create_user", service_type="admin_directory")
async def create_user(
    service,
    user_google_email: str,
    primary_email: str,
    given_name: str,
    family_name: str,
    password: str,
    org_unit_path: str = "/",
    change_password_at_next_login: bool = True,
) -> str:
    """
    Create a new user.

    Args:
        user_google_email (str): The user's Google email address. Required.
        primary_email (str): The primary email address for the new user.
        given_name (str): The user's first name.
        family_name (str): The user's last name.
        password (str): The initial password for the user.
        org_unit_path (str): The full path of the parent organization. Defaults to "/".
        change_password_at_next_login (bool): Whether the user must change password at next login. Defaults to True.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[create_user] Invoked. Email: '{user_google_email}', New User: '{primary_email}'"
    )

    body = {
        "primaryEmail": primary_email,
        "name": {
            "givenName": given_name,
            "familyName": family_name,
        },
        "password": password,
        "orgUnitPath": org_unit_path,
        "changePasswordAtNextLogin": change_password_at_next_login,
    }

    result = await asyncio.to_thread(service.users().insert(body=body).execute)

    created_email = result.get("primaryEmail")
    return f"User {created_email} created successfully."


@server.tool()
@require_google_service("admin_directory", "admin_directory_user")
@handle_http_errors("suspend_user", service_type="admin_directory")
async def suspend_user(
    service,
    user_google_email: str,
    user_key: str,
) -> str:
    """
    Suspend a user.

    Args:
        user_google_email (str): The user's Google email address. Required.
        user_key (str): The user's primary email address or unique ID.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[suspend_user] Invoked. Email: '{user_google_email}', User Key: '{user_key}'"
    )

    body = {"suspended": True}
    await asyncio.to_thread(
        service.users().update(userKey=user_key, body=body).execute
    )

    return f"User {user_key} has been suspended."


@server.tool()
@require_google_service("admin_directory", "admin_directory_user")
@handle_http_errors("restore_user", service_type="admin_directory")
async def restore_user(
    service,
    user_google_email: str,
    user_key: str,
) -> str:
    """
    Restore (unsuspend) a user.

    Args:
        user_google_email (str): The user's Google email address. Required.
        user_key (str): The user's primary email address or unique ID.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[restore_user] Invoked. Email: '{user_google_email}', User Key: '{user_key}'"
    )

    body = {"suspended": False}
    await asyncio.to_thread(
        service.users().update(userKey=user_key, body=body).execute
    )

    return f"User {user_key} has been restored."


# --- Group Management Tools ---


@server.tool()
@require_google_service("admin_directory", "admin_directory_group_readonly")
@handle_http_errors("list_groups", service_type="admin_directory")
async def list_groups(
    service,
    user_google_email: str,
    domain: Optional[str] = None,
    user_key: Optional[str] = None,
    page_size: int = 100,
    page_token: Optional[str] = None,
) -> str:
    """
    List groups in the domain.

    Args:
        user_google_email (str): The user's Google email address. Required.
        domain (Optional[str]): The domain name to list groups from.
        user_key (Optional[str]): Email or ID of a user to list groups for (groups the user is a member of).
        page_size (int): Maximum number of groups to return. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of groups.
    """
    logger.info(f"[list_groups] Invoked. Email: '{user_google_email}'")

    params = {"customer": "my_customer", "maxResults": page_size}
    if domain:
        params["domain"] = domain
    if user_key:
        params["userKey"] = user_key
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(service.groups().list(**params).execute)

    groups = result.get("groups", [])
    next_page_token = result.get("nextPageToken")

    if not groups:
        return "No groups found."

    output = [f"Found {len(groups)} groups:"]
    for group in groups:
        email = group.get("email", "Unknown Email")
        name = group.get("name", "Unknown Name")
        direct_members = group.get("directMembersCount", "Unknown")
        output.append(f"- {name} <{email}> (Members: {direct_members})")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("admin_directory", "admin_directory_group_readonly")
@handle_http_errors("get_group", service_type="admin_directory")
async def get_group(
    service,
    user_google_email: str,
    group_key: str,
) -> str:
    """
    Get details of a specific group.

    Args:
        user_google_email (str): The user's Google email address. Required.
        group_key (str): The group's email address or unique ID.

    Returns:
        str: Group details.
    """
    logger.info(
        f"[get_group] Invoked. Email: '{user_google_email}', Group Key: '{group_key}'"
    )

    group = await asyncio.to_thread(service.groups().get(groupKey=group_key).execute)

    name = group.get("name", "Unknown Name")
    email = group.get("email", "Unknown Email")
    description = group.get("description", "No description")
    direct_members = group.get("directMembersCount", "Unknown")
    admin_created = group.get("adminCreated", False)

    result = f"""Group Details for {group_key}:
- Name: {name}
- Email: {email}
- Description: {description}
- Members Count: {direct_members}
- Admin Created: {admin_created}"""

    return result


@server.tool()
@require_google_service("admin_directory", "admin_directory_group")
@handle_http_errors("create_group", service_type="admin_directory")
async def create_group(
    service,
    user_google_email: str,
    email: str,
    name: str,
    description: Optional[str] = None,
) -> str:
    """
    Create a new group.

    Args:
        user_google_email (str): The user's Google email address. Required.
        email (str): The group's email address.
        name (str): The group's name.
        description (Optional[str]): The group's description.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[create_group] Invoked. Email: '{user_google_email}', New Group: '{email}'"
    )

    body = {
        "email": email,
        "name": name,
    }
    if description:
        body["description"] = description

    result = await asyncio.to_thread(service.groups().insert(body=body).execute)

    created_email = result.get("email")
    return f"Group {created_email} created successfully."


@server.tool()
@require_google_service("admin_directory", "admin_directory_group")
@handle_http_errors("delete_group", service_type="admin_directory")
async def delete_group(
    service,
    user_google_email: str,
    group_key: str,
) -> str:
    """
    Delete a group.

    Args:
        user_google_email (str): The user's Google email address. Required.
        group_key (str): The group's email address or unique ID.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[delete_group] Invoked. Email: '{user_google_email}', Group Key: '{group_key}'"
    )

    await asyncio.to_thread(service.groups().delete(groupKey=group_key).execute)

    return f"Group {group_key} deleted successfully."


@server.tool()
@require_google_service("admin_directory", "admin_directory_group_member")
@handle_http_errors("add_group_member", service_type="admin_directory")
async def add_group_member(
    service,
    user_google_email: str,
    group_key: str,
    member_email: str,
    role: str = "MEMBER",
) -> str:
    """
    Add a member to a group.

    Args:
        user_google_email (str): The user's Google email address. Required.
        group_key (str): The group's email address or unique ID.
        member_email (str): The email address of the user or group to add.
        role (str): The role of the member ("MEMBER", "OWNER", "MANAGER"). Defaults to "MEMBER".

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[add_group_member] Invoked. Email: '{user_google_email}', Group: '{group_key}', Member: '{member_email}'"
    )

    body = {
        "email": member_email,
        "role": role,
    }

    await asyncio.to_thread(
        service.members().insert(groupKey=group_key, body=body).execute
    )

    return f"Added {member_email} to group {group_key} as {role}."


@server.tool()
@require_google_service("admin_directory", "admin_directory_group_member")
@handle_http_errors("remove_group_member", service_type="admin_directory")
async def remove_group_member(
    service,
    user_google_email: str,
    group_key: str,
    member_email: str,
) -> str:
    """
    Remove a member from a group.

    Args:
        user_google_email (str): The user's Google email address. Required.
        group_key (str): The group's email address or unique ID.
        member_email (str): The email address of the member to remove.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[remove_group_member] Invoked. Email: '{user_google_email}', Group: '{group_key}', Member: '{member_email}'"
    )

    await asyncio.to_thread(
        service.members().delete(groupKey=group_key, memberKey=member_email).execute
    )

    return f"Removed {member_email} from group {group_key}."


@server.tool()
@require_google_service("admin_directory", "admin_directory_group_member_readonly")
@handle_http_errors("list_group_members", service_type="admin_directory")
async def list_group_members(
    service,
    user_google_email: str,
    group_key: str,
    page_size: int = 100,
    page_token: Optional[str] = None,
) -> str:
    """
    List members of a group.

    Args:
        user_google_email (str): The user's Google email address. Required.
        group_key (str): The group's email address or unique ID.
        page_size (int): Maximum number of members to return. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of group members.
    """
    logger.info(
        f"[list_group_members] Invoked. Email: '{user_google_email}', Group: '{group_key}'"
    )

    params = {"groupKey": group_key, "maxResults": page_size}
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(service.members().list(**params).execute)

    members = result.get("members", [])
    next_page_token = result.get("nextPageToken")

    if not members:
        return f"No members found in group {group_key}."

    output = [f"Members of {group_key}:"]
    for member in members:
        email = member.get("email", "Unknown Email")
        role = member.get("role", "Unknown Role")
        type_ = member.get("type", "Unknown Type")
        output.append(f"- {email} ({role}, {type_})")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)
