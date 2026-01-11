"""
Google Meet API Tools

This module provides MCP tools for interacting with the Google Meet API.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@require_google_service("meet", "meet_conference_records_read")
@handle_http_errors("list_conference_records", service_type="meet")
async def list_conference_records(
    service,
    user_google_email: str,
    page_size: int = 10,
    page_token: Optional[str] = None,
    filter_str: Optional[str] = None,
) -> str:
    """
    List conference records.

    Args:
        user_google_email (str): The user's Google email address. Required.
        page_size (int): Maximum number of records to return. Defaults to 10.
        page_token (Optional[str]): Token for the next page of results.
        filter_str (Optional[str]): Filter string. e.g. "startTime >= '2023-01-01T00:00:00Z'"

    Returns:
        str: A list of conference records.
    """
    logger.info(f"[list_conference_records] Invoked. Email: '{user_google_email}'")

    params = {"pageSize": page_size}
    if page_token:
        params["pageToken"] = page_token
    if filter_str:
        params["filter"] = filter_str

    result = await asyncio.to_thread(service.conferenceRecords().list(**params).execute)

    records = result.get("conferenceRecords", [])
    next_page_token = result.get("nextPageToken")

    if not records:
        return "No conference records found."

    output = [f"Found {len(records)} conference records:"]
    for record in records:
        name = record.get("name")  # Resource name
        start_time = record.get("startTime", "Unknown Start")
        end_time = record.get("endTime", "Unknown End")

        output.append(f"- {name} (Start: {start_time}, End: {end_time})")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("meet", "meet_conference_records_read")
@handle_http_errors("get_conference_record", service_type="meet")
async def get_conference_record(
    service,
    user_google_email: str,
    conference_record_name: str,
) -> str:
    """
    Get a conference record by name.

    Args:
        user_google_email (str): The user's Google email address. Required.
        conference_record_name (str): The resource name of the conference record (e.g. "conferenceRecords/abc-def-ghi").

    Returns:
        str: Conference record details.
    """
    logger.info(
        f"[get_conference_record] Invoked. Email: '{user_google_email}', Name: '{conference_record_name}'"
    )

    record = await asyncio.to_thread(
        service.conferenceRecords().get(name=conference_record_name).execute
    )

    name = record.get("name")
    start_time = record.get("startTime", "Unknown Start")
    end_time = record.get("endTime", "Unknown End")
    expire_time = record.get("expireTime", "Unknown Expiry")
    space = record.get("space", "Unknown Space")

    result = f"""Conference Record: {name}
- Start Time: {start_time}
- End Time: {end_time}
- Expire Time: {expire_time}
- Space: {space}"""

    return result
