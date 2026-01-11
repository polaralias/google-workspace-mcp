"""
Google People API Tools

This module provides MCP tools for interacting with the Google People API.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@require_google_service("people", "people_contacts_read")
@handle_http_errors("list_contacts", service_type="people")
async def list_contacts(
    service,
    user_google_email: str,
    page_size: int = 100,
    page_token: Optional[str] = None,
    sort_order: str = "LAST_MODIFIED_DESCENDING",
) -> str:
    """
    List the user's contacts.

    Args:
        user_google_email (str): The user's Google email address. Required.
        page_size (int): Number of contacts to return per page. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.
        sort_order (str): Sort order for contacts. Defaults to "LAST_MODIFIED_DESCENDING".
            Values: "LAST_MODIFIED_DESCENDING", "FIRST_NAME_ASCENDING", "LAST_NAME_ASCENDING".

    Returns:
        str: A list of contacts.
    """
    logger.info(
        f"[list_contacts] Invoked. Email: '{user_google_email}', Sort: '{sort_order}'"
    )

    params = {
        "resourceName": "people/me",
        "personFields": "names,emailAddresses,phoneNumbers,organizations",
        "pageSize": page_size,
        "sortOrder": sort_order,
    }
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(
        service.people().connections().list(**params).execute
    )

    connections = result.get("connections", [])
    next_page_token = result.get("nextPageToken")

    if not connections:
        return "No contacts found."

    output = [f"Found {len(connections)} contacts:"]
    for person in connections:
        resource_name = person.get("resourceName")

        names = person.get("names", [])
        display_name = names[0].get("displayName") if names else "Unknown Name"

        emails = person.get("emailAddresses", [])
        email_list = [e.get("value") for e in emails]
        email_str = ", ".join(email_list) if email_list else "No Email"

        output.append(f"- {display_name} ({email_str}) [{resource_name}]")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("people", "people_contacts_read")
@handle_http_errors("search_contacts", service_type="people")
async def search_contacts(
    service,
    user_google_email: str,
    query: str,
    read_mask: str = "names,emailAddresses,phoneNumbers",
    page_size: int = 10,
) -> str:
    """
    Search for contacts.

    Args:
        user_google_email (str): The user's Google email address. Required.
        query (str): The search query.
        read_mask (str): Comma-separated list of fields to fetch. Defaults to "names,emailAddresses,phoneNumbers".
        page_size (int): Maximum number of results to return. Defaults to 10.

    Returns:
        str: Search results.
    """
    logger.info(f"[search_contacts] Invoked. Email: '{user_google_email}', Query: '{query}'")

    params = {
        "query": query,
        "readMask": read_mask,
    }

    # searchContacts does not have a 'limit' param in the same way, but pageSize might work if supported or we slice results.
    # The API documentation says 'pageSize' (default 10).
    params["pageSize"] = page_size

    result = await asyncio.to_thread(service.people().searchContacts(**params).execute)

    results = result.get("results", [])

    if not results:
        return f"No contacts found matching '{query}'."

    output = [f"Found {len(results)} matches for '{query}':"]
    for item in results:
        person = item.get("person", {})
        resource_name = person.get("resourceName")

        names = person.get("names", [])
        display_name = names[0].get("displayName") if names else "Unknown Name"

        emails = person.get("emailAddresses", [])
        email_list = [e.get("value") for e in emails]
        email_str = ", ".join(email_list) if email_list else "No Email"

        output.append(f"- {display_name} ({email_str}) [{resource_name}]")

    return "\n".join(output)


@server.tool()
@require_google_service("people", "people_contacts")
@handle_http_errors("create_contact", service_type="people")
async def create_contact(
    service,
    user_google_email: str,
    given_name: str,
    family_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> str:
    """
    Create a new contact.

    Args:
        user_google_email (str): The user's Google email address. Required.
        given_name (str): The contact's given name (first name).
        family_name (Optional[str]): The contact's family name (last name).
        email (Optional[str]): The contact's email address.
        phone (Optional[str]): The contact's phone number.

    Returns:
        str: Confirmation message with the new contact's resource name.
    """
    logger.info(
        f"[create_contact] Invoked. Email: '{user_google_email}', Name: '{given_name} {family_name}'"
    )

    body = {
        "names": [{"givenName": given_name}]
    }

    if family_name:
        body["names"][0]["familyName"] = family_name

    if email:
        body["emailAddresses"] = [{"value": email, "type": "home"}]

    if phone:
        body["phoneNumbers"] = [{"value": phone, "type": "mobile"}]

    result = await asyncio.to_thread(
        service.people().createContact(body=body).execute
    )

    resource_name = result.get("resourceName")
    return f"Contact created successfully: {resource_name}"


@server.tool()
@require_google_service("people", "people_contacts")
@handle_http_errors("update_contact", service_type="people")
async def update_contact(
    service,
    user_google_email: str,
    resource_name: str,
    etag: str,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> str:
    """
    Update an existing contact.

    This implementation first fetches the contact to preserve existing fields not being updated,
    then merges the new values and sends the update.

    Args:
        user_google_email (str): The user's Google email address. Required.
        resource_name (str): The resource name of the contact (e.g., "people/c12345").
        etag (str): The etag of the contact. Required for updates.
        given_name (Optional[str]): New given name.
        family_name (Optional[str]): New family name.
        email (Optional[str]): New email address.
        phone (Optional[str]): New phone number.

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[update_contact] Invoked. Email: '{user_google_email}', Resource: '{resource_name}'"
    )

    # 1. Fetch existing contact
    existing_contact = await asyncio.to_thread(
        service.people().get(
            resourceName=resource_name,
            personFields="names,emailAddresses,phoneNumbers"
        ).execute
    )

    # 2. Prepare body with existing etag
    body = {"etag": etag}
    update_fields = []

    # 3. Merge Names
    if given_name or family_name:
        # Get existing name or create new structure
        current_names = existing_contact.get("names", [])
        if current_names:
            target_name = current_names[0] # Modify primary name
        else:
            target_name = {}
            current_names = [target_name]

        if given_name:
            target_name["givenName"] = given_name
        if family_name:
            target_name["familyName"] = family_name

        body["names"] = current_names
        update_fields.append("names")

    # 4. Merge Emails
    if email:
        # Strategy: Add as new email if not present, or replace?
        # For simplicity in this tool: If we provide an email, we append it if unique,
        # or we could act as a replacement.
        # Let's assume we want to ADD this email or Update if type 'home' exists.
        # But robust merging is hard.
        # Let's try to find an existing email of type 'home' and update it, or add new.

        current_emails = existing_contact.get("emailAddresses", [])
        found = False
        for e in current_emails:
            if e.get("type") == "home":
                e["value"] = email
                found = True
                break

        if not found:
            current_emails.append({"value": email, "type": "home"})

        body["emailAddresses"] = current_emails
        update_fields.append("emailAddresses")

    # 5. Merge Phones
    if phone:
        current_phones = existing_contact.get("phoneNumbers", [])
        found = False
        for p in current_phones:
            if p.get("type") == "mobile":
                p["value"] = phone
                found = True
                break

        if not found:
            current_phones.append({"value": phone, "type": "mobile"})

        body["phoneNumbers"] = current_phones
        update_fields.append("phoneNumbers")

    if not update_fields:
        return "No fields specified for update."

    params = {
        "resourceName": resource_name,
        "updatePersonFields": ",".join(update_fields),
        "body": body
    }

    result = await asyncio.to_thread(
        service.people().updateContact(**params).execute
    )

    return f"Contact {resource_name} updated successfully."


@server.tool()
@require_google_service("people", "people_contacts")
@handle_http_errors("delete_contact", service_type="people")
async def delete_contact(
    service,
    user_google_email: str,
    resource_name: str,
) -> str:
    """
    Delete a contact.

    Args:
        user_google_email (str): The user's Google email address. Required.
        resource_name (str): The resource name of the contact to delete (e.g., "people/c12345").

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[delete_contact] Invoked. Email: '{user_google_email}', Resource: '{resource_name}'"
    )

    await asyncio.to_thread(
        service.people().deleteContact(resourceName=resource_name).execute
    )

    return f"Contact {resource_name} deleted successfully."


@server.tool()
@require_google_service("people", "people_contacts_read")
@handle_http_errors("list_other_contacts", service_type="people")
async def list_other_contacts(
    service,
    user_google_email: str,
    page_size: int = 100,
    page_token: Optional[str] = None,
    read_mask: str = "names,emailAddresses,phoneNumbers",
) -> str:
    """
    List "Other contacts" (frequently contacted).

    Args:
        user_google_email (str): The user's Google email address. Required.
        page_size (int): Number of contacts to return per page. Defaults to 100.
        page_token (Optional[str]): Token for the next page of results.
        read_mask (str): Comma-separated list of fields to fetch. Defaults to "names,emailAddresses,phoneNumbers".

    Returns:
        str: A list of other contacts.
    """
    logger.info(f"[list_other_contacts] Invoked. Email: '{user_google_email}'")

    params = {
        "pageSize": page_size,
        "readMask": read_mask,
    }
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(
        service.otherContacts().list(**params).execute
    )

    other_contacts = result.get("otherContacts", [])
    next_page_token = result.get("nextPageToken")

    if not other_contacts:
        return "No other contacts found."

    output = [f"Found {len(other_contacts)} other contacts:"]
    for contact in other_contacts:
        resource_name = contact.get("resourceName")

        names = contact.get("names", [])
        display_name = names[0].get("displayName") if names else "Unknown Name"

        emails = contact.get("emailAddresses", [])
        email_list = [e.get("value") for e in emails]
        email_str = ", ".join(email_list) if email_list else "No Email"

        output.append(f"- {display_name} ({email_str}) [{resource_name}]")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)


@server.tool()
@require_google_service("people", "people_directory_read")
@handle_http_errors("search_directory_people", service_type="people")
async def search_directory_people(
    service,
    user_google_email: str,
    query: str,
    read_mask: str = "names,emailAddresses,phoneNumbers",
    page_size: int = 10,
    page_token: Optional[str] = None,
) -> str:
    """
    Search the directory for people.

    Args:
        user_google_email (str): The user's Google email address. Required.
        query (str): The search query.
        read_mask (str): Comma-separated list of fields to fetch. Defaults to "names,emailAddresses,phoneNumbers".
        page_size (int): Maximum number of results to return. Defaults to 10.
        page_token (Optional[str]): Token for the next page of results.

    Returns:
        str: Search results from the directory.
    """
    logger.info(f"[search_directory_people] Invoked. Email: '{user_google_email}', Query: '{query}'")

    params = {
        "query": query,
        "readMask": read_mask,
        "pageSize": page_size,
        "sources": ["DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE", "DIRECTORY_SOURCE_TYPE_DOMAIN_CONTACT"]
    }
    if page_token:
        params["pageToken"] = page_token

    result = await asyncio.to_thread(
        service.people().searchDirectoryPeople(**params).execute
    )

    people = result.get("people", [])
    next_page_token = result.get("nextPageToken")

    if not people:
        return f"No directory people found matching '{query}'."

    output = [f"Found {len(people)} directory matches:"]
    for person in people:
        resource_name = person.get("resourceName")

        names = person.get("names", [])
        display_name = names[0].get("displayName") if names else "Unknown Name"

        emails = person.get("emailAddresses", [])
        email_list = [e.get("value") for e in emails]
        email_str = ", ".join(email_list) if email_list else "No Email"

        output.append(f"- {display_name} ({email_str}) [{resource_name}]")

    if next_page_token:
        output.append(f"\nNext page token: {next_page_token}")

    return "\n".join(output)
