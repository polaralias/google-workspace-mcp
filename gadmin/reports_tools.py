"""
Google Admin SDK Reports API Tools

This module provides MCP tools for interacting with the Google Admin SDK Reports API.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@require_google_service("admin_reports", "admin_reports_audit_readonly")
@handle_http_errors("list_admin_activities", service_type="admin_reports")
async def list_admin_activities(
    service,
    user_google_email: str,
    application_name: str,
    user_key: str = "all",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_name: Optional[str] = None,
    max_results: int = 100,
    page_token: Optional[str] = None,
) -> str:
    """
    List activities from the Admin SDK Reports API.

    Args:
        user_google_email (str): The user's Google email address. Required.
        application_name (str): Application name for which the events are to be retrieved.
            Examples: "admin", "calendar", "drive", "login", "mobile", "token", "groups", "saml", "chat", "gcp", "rules", "meet", "user_accounts".
        user_key (str): Represents the profile ID or the user email for which the data should be filtered. Defaults to "all".
        start_time (Optional[str]): Return events which occurred at or after this time (RFC 3339 format).
        end_time (Optional[str]): Return events which occurred at or before this time (RFC 3339 format).
        event_name (Optional[str]): Name of the event being queried.
        max_results (int): Maximum number of events to return. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of activity events.
    """
    logger.info(
        f"[list_admin_activities] Invoked. Email: '{user_google_email}', App: '{application_name}', User: '{user_key}'"
    )

    params = {
        "userKey": user_key,
        "applicationName": application_name,
        "maxResults": max_results,
    }
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time
    if event_name:
        params["eventName"] = event_name
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(service.activities().list(**params).execute)

    items = result.get("items", [])
    next_page_token = result.get("nextPageToken")

    if not items:
        return f"No activities found for application '{application_name}'."

    output = [f"Activities for {application_name} (User: {user_key}):"]
    for item in items:
        actor_email = item.get("actor", {}).get("email", "Unknown Actor")
        ip_address = item.get("ipAddress", "Unknown IP")
        time = item.get("id", {}).get("time", "Unknown Time")

        events = item.get("events", [])
        event_descriptions = []
        for event in events:
            name = event.get("name", "Unknown Event")
            params_list = event.get("parameters", [])
            param_str = ", ".join(
                [f"{p.get('name')}={p.get('value')}" for p in params_list]
            )
            event_descriptions.append(f"{name} [{param_str}]")

        events_str = "; ".join(event_descriptions)
        output.append(f"- [{time}] {actor_email} ({ip_address}): {events_str}")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("admin_reports", "admin_reports_audit_readonly")
@handle_http_errors("list_drive_activities_via_reports", service_type="admin_reports")
async def list_drive_activities_via_reports(
    service,
    user_google_email: str,
    user_key: str = "all",
    start_time: Optional[str] = None,
    max_results: int = 50,
) -> str:
    """
    Convenience tool to list Drive activities specifically via Reports API.

    Args:
        user_google_email (str): The user's Google email address. Required.
        user_key (str): The profile ID or the user email. Defaults to "all".
        start_time (Optional[str]): Return events which occurred at or after this time (RFC 3339 format).
        max_results (int): Maximum number of events to return. Defaults to 50.

    Returns:
        str: A list of Drive activities.
    """
    logger.info(
        f"[list_drive_activities_via_reports] Invoked. Email: '{user_google_email}', User: '{user_key}'"
    )

    return await list_admin_activities(
        service,
        user_google_email,
        application_name="drive",
        user_key=user_key,
        start_time=start_time,
        max_results=max_results,
    )
