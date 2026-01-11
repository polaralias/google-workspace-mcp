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


@server.tool()
@require_google_service("meet", "meet_conference_records_read")
@handle_http_errors("list_conference_participants", service_type="meet")
async def list_conference_participants(
    service,
    user_google_email: str,
    conference_record_name: str,
    page_size: int = 100,
    page_token: Optional[str] = None,
) -> str:
    """
    List participants of a conference record.

    Args:
        user_google_email (str): The user's Google email address. Required.
        conference_record_name (str): The resource name of the conference record (e.g. "conferenceRecords/abc-def-ghi").
        page_size (int): Maximum number of participants to return. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of conference participants.
    """
    logger.info(
        f"[list_conference_participants] Invoked. Email: '{user_google_email}', Record: '{conference_record_name}'"
    )

    params = {
        "parent": conference_record_name,
        "pageSize": page_size
    }
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(
        service.conferenceRecords().participants().list(**params).execute
    )

    participants = result.get("participants", [])
    next_page_token = result.get("nextPageToken")

    if not participants:
        return f"No participants found for conference record '{conference_record_name}'."

    output = [f"Found {len(participants)} participants:"]
    for participant in participants:
        name = participant.get("name") # Resource name: conferenceRecords/{id}/participants/{id}

        # Determine caller/device info if available
        # Note: Participants resource structure depends on if it's signed-in user or anonymous/phone.
        # Signed-in user: signedinUser: { user: ... }
        # Anonymous: anonymousUser: { displayName: ... }
        # Phone: phoneUser: { displayName: ... }

        display_text = "Unknown Participant"

        if "signedinUser" in participant:
            user = participant["signedinUser"].get("user", "")
            display_text = f"Signed-in User ({user})"
        elif "anonymousUser" in participant:
            display_name = participant["anonymousUser"].get("displayName", "Anonymous")
            display_text = f"Anonymous User ({display_name})"
        elif "phoneUser" in participant:
            display_name = participant["phoneUser"].get("displayName", "Phone")
            display_text = f"Phone User ({display_name})"

        earliest_start_time = participant.get("earliestStartTime", "Unknown Start")
        latest_end_time = participant.get("latestEndTime", "Unknown End")

        output.append(f"- {display_text} [{name}] (Time: {earliest_start_time} - {latest_end_time})")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("meet", "meet_conference_records_read")
@handle_http_errors("list_conference_recordings", service_type="meet")
async def list_conference_recordings(
    service,
    user_google_email: str,
    conference_record_name: str,
    page_size: int = 10,
    page_token: Optional[str] = None,
) -> str:
    """
    List recordings of a conference record.

    Args:
        user_google_email (str): The user's Google email address. Required.
        conference_record_name (str): The resource name of the conference record (e.g. "conferenceRecords/abc-def-ghi").
        page_size (int): Maximum number of recordings to return. Defaults to 10.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of conference recordings.
    """
    logger.info(
        f"[list_conference_recordings] Invoked. Email: '{user_google_email}', Record: '{conference_record_name}'"
    )

    params = {
        "parent": conference_record_name,
        "pageSize": page_size
    }
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(
        service.conferenceRecords().recordings().list(**params).execute
    )

    recordings = result.get("recordings", [])
    next_page_token = result.get("nextPageToken")

    if not recordings:
        return f"No recordings found for conference record '{conference_record_name}'."

    output = [f"Found {len(recordings)} recordings:"]
    for recording in recordings:
        name = recording.get("name")
        state = recording.get("state", "UNKNOWN")
        start_time = recording.get("startTime", "Unknown Start")
        drive_dest = recording.get("driveDestination", {})
        file = drive_dest.get("file", "No Drive File")
        export_uri = drive_dest.get("exportUri", "No Export URI")

        output.append(f"- {name} [State: {state}] (Start: {start_time})\n  File: {file}\n  URI: {export_uri}")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("meet", "meet_conference_records_read")
@handle_http_errors("list_conference_transcripts", service_type="meet")
async def list_conference_transcripts(
    service,
    user_google_email: str,
    conference_record_name: str,
    page_size: int = 10,
    page_token: Optional[str] = None,
) -> str:
    """
    List transcripts of a conference record.

    Args:
        user_google_email (str): The user's Google email address. Required.
        conference_record_name (str): The resource name of the conference record (e.g. "conferenceRecords/abc-def-ghi").
        page_size (int): Maximum number of transcripts to return. Defaults to 10.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: A list of conference transcripts.
    """
    logger.info(
        f"[list_conference_transcripts] Invoked. Email: '{user_google_email}', Record: '{conference_record_name}'"
    )

    params = {
        "parent": conference_record_name,
        "pageSize": page_size
    }
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(
        service.conferenceRecords().transcripts().list(**params).execute
    )

    transcripts = result.get("transcripts", [])
    next_page_token = result.get("nextPageToken")

    if not transcripts:
        return f"No transcripts found for conference record '{conference_record_name}'."

    output = [f"Found {len(transcripts)} transcripts:"]
    for transcript in transcripts:
        name = transcript.get("name")
        state = transcript.get("state", "UNKNOWN")
        start_time = transcript.get("startTime", "Unknown Start")
        docs_dest = transcript.get("docsDestination", {})
        document = docs_dest.get("document", "No Doc")
        export_uri = docs_dest.get("exportUri", "No Export URI")

        output.append(f"- {name} [State: {state}] (Start: {start_time})\n  Doc: {document}\n  URI: {export_uri}")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)
