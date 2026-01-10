"""
Google Slides MCP Tools

This module provides MCP tools for interacting with Google Slides API.
"""

import logging
import asyncio
import io
from typing import List, Dict, Any, Optional
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from auth.service_decorator import require_google_service, require_multiple_services
from core.server import server
from core.utils import handle_http_errors
from core.comments import create_comment_tools

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("create_presentation", service_type="slides")
@require_google_service("slides", "slides")
async def create_presentation(
    service, user_google_email: str, title: str = "Untitled Presentation"
) -> str:
    """
    Create a new Google Slides presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        title (str): The title for the new presentation. Defaults to "Untitled Presentation".

    Returns:
        str: Details about the created presentation including ID and URL.
    """
    logger.info(
        f"[create_presentation] Invoked. Email: '{user_google_email}', Title: '{title}'"
    )

    body = {"title": title}

    result = await asyncio.to_thread(service.presentations().create(body=body).execute)

    presentation_id = result.get("presentationId")
    presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    confirmation_message = f"""Presentation Created Successfully for {user_google_email}:
- Title: {title}
- Presentation ID: {presentation_id}
- URL: {presentation_url}
- Slides: {len(result.get("slides", []))} slide(s) created"""

    logger.info(f"Presentation created successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("get_presentation", is_read_only=True, service_type="slides")
@require_google_service("slides", "slides_read")
async def get_presentation(
    service, user_google_email: str, presentation_id: str
) -> str:
    """
    Get details about a Google Slides presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation to retrieve.

    Returns:
        str: Details about the presentation including title, slides count, and metadata.
    """
    logger.info(
        f"[get_presentation] Invoked. Email: '{user_google_email}', ID: '{presentation_id}'"
    )

    result = await asyncio.to_thread(
        service.presentations().get(presentationId=presentation_id).execute
    )

    title = result.get("title", "Untitled")
    slides = result.get("slides", [])
    page_size = result.get("pageSize", {})

    slides_info = []
    for i, slide in enumerate(slides, 1):
        slide_id = slide.get("objectId", "Unknown")
        page_elements = slide.get("pageElements", [])

        # Collect text from the slide whose JSON structure is very complicated
        # https://googleapis.github.io/google-api-python-client/docs/dyn/slides_v1.presentations.html#get
        slide_text = ""
        try:
            texts_from_elements = []
            for page_element in slide.get("pageElements", []):
                shape = page_element.get("shape", None)
                if shape and shape.get("text", None):
                    text = shape.get("text", None)
                    if text:
                        text_elements_in_shape = []
                        for text_element in text.get("textElements", []):
                            text_run = text_element.get("textRun", None)
                            if text_run:
                                content = text_run.get("content", None)
                                if content:
                                    start_index = text_element.get("startIndex", 0)
                                    text_elements_in_shape.append(
                                        (start_index, content)
                                    )

                        if text_elements_in_shape:
                            # Sort text elements within a single shape
                            text_elements_in_shape.sort(key=lambda item: item[0])
                            full_text_from_shape = "".join(
                                [item[1] for item in text_elements_in_shape]
                            )
                            texts_from_elements.append(full_text_from_shape)

            # cleanup text we collected
            slide_text = "\n".join(texts_from_elements)
            slide_text_rows = slide_text.split("\n")
            slide_text_rows = [row for row in slide_text_rows if len(row.strip()) > 0]
            if slide_text_rows:
                slide_text_rows = ["    > " + row for row in slide_text_rows]
                slide_text = "\n" + "\n".join(slide_text_rows)
            else:
                slide_text = ""
        except Exception as e:
            logger.warning(f"Failed to extract text from the slide {slide_id}: {e}")
            slide_text = f"<failed to extract text: {type(e)}, {e}>"

        slides_info.append(
            f"  Slide {i}: ID {slide_id}, {len(page_elements)} element(s), text: {slide_text if slide_text else 'empty'}"
        )

    confirmation_message = f"""Presentation Details for {user_google_email}:
- Title: {title}
- Presentation ID: {presentation_id}
- URL: https://docs.google.com/presentation/d/{presentation_id}/edit
- Total Slides: {len(slides)}
- Page Size: {page_size.get("width", {}).get("magnitude", "Unknown")} x {page_size.get("height", {}).get("magnitude", "Unknown")} {page_size.get("width", {}).get("unit", "")}

Slides Breakdown:
{chr(10).join(slides_info) if slides_info else "  No slides found"}"""

    logger.info(f"Presentation retrieved successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("batch_update_presentation", service_type="slides")
@require_google_service("slides", "slides")
async def batch_update_presentation(
    service,
    user_google_email: str,
    presentation_id: str,
    requests: List[Dict[str, Any]],
) -> str:
    """
    Apply batch updates to a Google Slides presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation to update.
        requests (List[Dict[str, Any]]): List of update requests to apply.

    Returns:
        str: Details about the batch update operation results.
    """
    logger.info(
        f"[batch_update_presentation] Invoked. Email: '{user_google_email}', ID: '{presentation_id}', Requests: {len(requests)}"
    )

    body = {"requests": requests}

    result = await asyncio.to_thread(
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body=body)
        .execute
    )

    replies = result.get("replies", [])

    confirmation_message = f"""Batch Update Completed for {user_google_email}:
- Presentation ID: {presentation_id}
- URL: https://docs.google.com/presentation/d/{presentation_id}/edit
- Requests Applied: {len(requests)}
- Replies Received: {len(replies)}"""

    if replies:
        confirmation_message += "\n\nUpdate Results:"
        for i, reply in enumerate(replies, 1):
            if "createSlide" in reply:
                slide_id = reply["createSlide"].get("objectId", "Unknown")
                confirmation_message += (
                    f"\n  Request {i}: Created slide with ID {slide_id}"
                )
            elif "createShape" in reply:
                shape_id = reply["createShape"].get("objectId", "Unknown")
                confirmation_message += (
                    f"\n  Request {i}: Created shape with ID {shape_id}"
                )
            else:
                confirmation_message += f"\n  Request {i}: Operation completed"

    logger.info(f"Batch update completed successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("get_page", is_read_only=True, service_type="slides")
@require_google_service("slides", "slides_read")
async def get_page(
    service, user_google_email: str, presentation_id: str, page_object_id: str
) -> str:
    """
    Get details about a specific page (slide) in a presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        page_object_id (str): The object ID of the page/slide to retrieve.

    Returns:
        str: Details about the specific page including elements and layout.
    """
    logger.info(
        f"[get_page] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Page: '{page_object_id}'"
    )

    result = await asyncio.to_thread(
        service.presentations()
        .pages()
        .get(presentationId=presentation_id, pageObjectId=page_object_id)
        .execute
    )

    page_type = result.get("pageType", "Unknown")
    page_elements = result.get("pageElements", [])

    elements_info = []
    for element in page_elements:
        element_id = element.get("objectId", "Unknown")
        if "shape" in element:
            shape_type = element["shape"].get("shapeType", "Unknown")
            elements_info.append(f"  Shape: ID {element_id}, Type: {shape_type}")
        elif "table" in element:
            table = element["table"]
            rows = table.get("rows", 0)
            cols = table.get("columns", 0)
            elements_info.append(f"  Table: ID {element_id}, Size: {rows}x{cols}")
        elif "line" in element:
            line_type = element["line"].get("lineType", "Unknown")
            elements_info.append(f"  Line: ID {element_id}, Type: {line_type}")
        else:
            elements_info.append(f"  Element: ID {element_id}, Type: Unknown")

    confirmation_message = f"""Page Details for {user_google_email}:
- Presentation ID: {presentation_id}
- Page ID: {page_object_id}
- Page Type: {page_type}
- Total Elements: {len(page_elements)}

Page Elements:
{chr(10).join(elements_info) if elements_info else "  No elements found"}"""

    logger.info(f"Page retrieved successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("get_page_thumbnail", is_read_only=True, service_type="slides")
@require_google_service("slides", "slides_read")
async def get_page_thumbnail(
    service,
    user_google_email: str,
    presentation_id: str,
    page_object_id: str,
    thumbnail_size: str = "MEDIUM",
) -> str:
    """
    Generate a thumbnail URL for a specific page (slide) in a presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        page_object_id (str): The object ID of the page/slide.
        thumbnail_size (str): Size of thumbnail ("LARGE", "MEDIUM", "SMALL"). Defaults to "MEDIUM".

    Returns:
        str: URL to the generated thumbnail image.
    """
    logger.info(
        f"[get_page_thumbnail] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Page: '{page_object_id}', Size: '{thumbnail_size}'"
    )

    result = await asyncio.to_thread(
        service.presentations()
        .pages()
        .getThumbnail(
            presentationId=presentation_id,
            pageObjectId=page_object_id,
            thumbnailProperties_thumbnailSize=thumbnail_size,
            thumbnailProperties_mimeType="PNG",
        )
        .execute
    )

    thumbnail_url = result.get("contentUrl", "")

    confirmation_message = f"""Thumbnail Generated for {user_google_email}:
- Presentation ID: {presentation_id}
- Page ID: {page_object_id}
- Thumbnail Size: {thumbnail_size}
- Thumbnail URL: {thumbnail_url}

You can view or download the thumbnail using the provided URL."""

    logger.info(f"Thumbnail generated successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("create_slide", service_type="slides")
@require_google_service("slides", "slides")
async def create_slide(
    service,
    user_google_email: str,
    presentation_id: str,
    layout: str = "TITLE_AND_BODY",
    insertion_index: Optional[int] = None,
) -> str:
    """
    Create a new slide in a presentation with a specified layout.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        layout (str): Predefined layout for the slide (e.g., 'TITLE_AND_BODY', 'TITLE_ONLY', 'BLANK'). Defaults to 'TITLE_AND_BODY'.
        insertion_index (Optional[int]): Zero-based index where the slide should be inserted. If None, appends to the end.

    Returns:
        str: Confirmation message with the new slide ID.
    """
    logger.info(
        f"[create_slide] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Layout: '{layout}'"
    )

    request: Dict[str, Any] = {
        "createSlide": {
            "slideLayoutReference": {"predefinedLayout": layout},
        }
    }

    if insertion_index is not None:
        request["createSlide"]["insertionIndex"] = insertion_index

    result = await asyncio.to_thread(
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": [request]})
        .execute
    )

    slide_id = (
        result.get("replies", [{}])[0].get("createSlide", {}).get("objectId", "Unknown")
    )
    link = f"https://docs.google.com/presentation/d/{presentation_id}/edit#slide=id.{slide_id}"

    confirmation_message = f"""Slide Created for {user_google_email}:
- Presentation ID: {presentation_id}
- New Slide ID: {slide_id}
- Layout: {layout}
- Link: {link}"""

    logger.info(f"Slide created successfully for {user_google_email}. ID: {slide_id}")
    return confirmation_message


@server.tool()
@handle_http_errors("add_textbox", service_type="slides")
@require_google_service("slides", "slides")
async def add_textbox(
    service,
    user_google_email: str,
    presentation_id: str,
    page_id: str,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    """
    Add a textbox with text to a specific slide.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        page_id (str): The ID of the slide where the textbox will be added.
        text (str): The text content of the textbox.
        x (float): The X coordinate (in points) for the top-left corner.
        y (float): The Y coordinate (in points) for the top-left corner.
        width (float): The width of the textbox (in points).
        height (float): The height of the textbox (in points).

    Returns:
        str: Confirmation message with the new textbox ID.
    """
    logger.info(
        f"[add_textbox] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Page: '{page_id}'"
    )

    # We need a random object ID for the createShape request if we want to refer to it immediately,
    # but normally the API generates one. However, to insert text immediately, we need the ID.
    # The API documentation says we can provide an ID, or let it generate.
    # If we let it generate, we can't insert text in the same batch unless we use the return value,
    # but batchUpdate takes a list of requests.
    # Wait, createShape returns the ID. But we want to do it in one go if possible?
    # Actually, we can just generate a client-side ID or rely on the fact that we can't do it in one batch
    # unless we specify the ID.
    # Let's generate a simplified random ID or just use a standard way if available.
    # Python's uuid can be used, but might be too long/complex.
    # Actually, many examples just use a generated string.
    import uuid

    element_id = f"textbox_{uuid.uuid4().hex}"

    requests = [
        {
            "createShape": {
                "objectId": element_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": page_id,
                    "size": {"width": {"magnitude": width, "unit": "PT"}, "height": {"magnitude": height, "unit": "PT"}},
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": x,
                        "translateY": y,
                        "unit": "PT",
                    },
                },
            }
        },
        {"insertText": {"objectId": element_id, "text": text}},
    ]

    await asyncio.to_thread(
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": requests})
        .execute
    )

    confirmation_message = f"""Textbox Added for {user_google_email}:
- Presentation ID: {presentation_id}
- Page ID: {page_id}
- Textbox ID: {element_id}
- Text: "{text}"
- Position: ({x}, {y})
- Size: {width}x{height}"""

    logger.info(f"Textbox added successfully for {user_google_email}. ID: {element_id}")
    return confirmation_message


@server.tool()
@handle_http_errors("set_text_style", service_type="slides")
@require_google_service("slides", "slides")
async def set_text_style(
    service,
    user_google_email: str,
    presentation_id: str,
    object_id: str,
    style_object: Dict[str, Any],
) -> str:
    """
    Update the style of text within a shape or table cell.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        object_id (str): The object ID of the shape or table.
        style_object (Dict[str, Any]): A dictionary representing the TextStyle to apply.
            Example: {"bold": True, "fontSize": {"magnitude": 14, "unit": "PT"}, "foregroundColor": {"opaqueColor": {"rgbColor": {"red": 1.0, "green": 0.0, "blue": 0.0}}}}

    Returns:
        str: Confirmation message.
    """
    logger.info(
        f"[set_text_style] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Object: '{object_id}'"
    )

    # fields mask is needed. We can infer it from the keys of style_object.
    fields = ",".join(style_object.keys())

    request = {
        "updateTextStyle": {
            "objectId": object_id,
            "style": style_object,
            "fields": fields,
        }
    }

    await asyncio.to_thread(
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": [request]})
        .execute
    )

    confirmation_message = f"""Text Style Updated for {user_google_email}:
- Presentation ID: {presentation_id}
- Object ID: {object_id}
- Fields Updated: {fields}"""

    logger.info(
        f"Text style updated successfully for {user_google_email}. Object: {object_id}"
    )
    return confirmation_message


@server.tool()
@handle_http_errors("replace_text_everywhere", service_type="slides")
@require_google_service("slides", "slides")
async def replace_text_everywhere(
    service,
    user_google_email: str,
    presentation_id: str,
    find_text: str,
    replace_text: str,
    match_case: bool = False,
) -> str:
    """
    Replace all instances of specified text throughout the presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        find_text (str): The text to search for.
        replace_text (str): The text to replace it with.
        match_case (bool): Whether to match case. Defaults to False.

    Returns:
        str: Confirmation message with number of occurrences changed.
    """
    logger.info(
        f"[replace_text_everywhere] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Find: '{find_text}'"
    )

    request = {
        "replaceAllText": {
            "containsText": {"text": find_text, "matchCase": match_case},
            "replaceText": replace_text,
        }
    }

    result = await asyncio.to_thread(
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": [request]})
        .execute
    )

    occurrences_changed = (
        result.get("replies", [{}])[0]
        .get("replaceAllText", {})
        .get("occurrencesChanged", 0)
    )

    confirmation_message = f"""Text Replacement Complete for {user_google_email}:
- Presentation ID: {presentation_id}
- Occurrences Changed: {occurrences_changed}
- Find: "{find_text}"
- Replace: "{replace_text}" """

    logger.info(
        f"Replaced {occurrences_changed} occurrences for {user_google_email} in presentation {presentation_id}"
    )
    return confirmation_message


@server.tool()
@handle_http_errors("insert_image_from_url", service_type="slides")
@require_google_service("slides", "slides")
async def insert_image_from_url(
    service,
    user_google_email: str,
    presentation_id: str,
    page_id: str,
    image_url: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    """
    Insert an image from a URL onto a slide.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation.
        page_id (str): The ID of the slide where the image will be added.
        image_url (str): The public URL of the image.
        x (float): The X coordinate (in points).
        y (float): The Y coordinate (in points).
        width (float): The width (in points).
        height (float): The height (in points).

    Returns:
        str: Confirmation message with the new image ID.
    """
    logger.info(
        f"[insert_image_from_url] Invoked. Email: '{user_google_email}', Presentation: '{presentation_id}', Page: '{page_id}', URL: '{image_url}'"
    )

    import uuid

    element_id = f"image_{uuid.uuid4().hex}"

    request = {
        "createImage": {
            "objectId": element_id,
            "url": image_url,
            "elementProperties": {
                "pageObjectId": page_id,
                "size": {"width": {"magnitude": width, "unit": "PT"}, "height": {"magnitude": height, "unit": "PT"}},
                "transform": {
                    "scaleX": 1,
                    "scaleY": 1,
                    "translateX": x,
                    "translateY": y,
                    "unit": "PT",
                },
            },
        }
    }

    await asyncio.to_thread(
        service.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": [request]})
        .execute
    )

    confirmation_message = f"""Image Inserted for {user_google_email}:
- Presentation ID: {presentation_id}
- Page ID: {page_id}
- Image ID: {element_id}
- URL: {image_url}
- Position: ({x}, {y})
- Size: {width}x{height}"""

    logger.info(f"Image inserted successfully for {user_google_email}. ID: {element_id}")
    return confirmation_message


@server.tool()
@handle_http_errors("export_presentation_pdf", service_type="drive")
@require_multiple_services(
    [
        {
            "service_type": "drive",
            "scopes": "drive_file",
            "param_name": "drive_service",
        },
        {
            "service_type": "slides",
            "scopes": "slides_read",
            "param_name": "slides_service",
        },
    ]
)
async def export_presentation_pdf(
    drive_service, slides_service, user_google_email: str, presentation_id: str
) -> str:
    """
    Export a presentation as a PDF and save it to Google Drive.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation to export.

    Returns:
        str: Confirmation message with details of the exported file.
    """
    logger.info(
        f"[export_presentation_pdf] Invoked. Email: '{user_google_email}', ID: '{presentation_id}'"
    )

    # 1. Get presentation details to verify it exists and get the title
    presentation = await asyncio.to_thread(
        slides_service.presentations().get(presentationId=presentation_id).execute
    )
    title = presentation.get("title", "Untitled Presentation")
    pdf_filename = f"{title}.pdf"

    # 2. Export the presentation using Drive API
    request_obj = drive_service.files().export_media(
        fileId=presentation_id, mimeType="application/pdf"
    )

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_obj)

    done = False
    while not done:
        _, done = await asyncio.to_thread(downloader.next_chunk)

    fh.seek(0)

    # 3. Upload the PDF back to Drive
    file_metadata = {"name": pdf_filename, "mimeType": "application/pdf"}

    media = MediaIoBaseUpload(fh, mimetype="application/pdf", resumable=True)

    uploaded_file = await asyncio.to_thread(
        drive_service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        )
        .execute
    )

    file_id = uploaded_file.get("id")
    web_link = uploaded_file.get("webViewLink")

    confirmation_message = f"""Presentation Exported as PDF for {user_google_email}:
- Original Presentation ID: {presentation_id}
- Exported File Name: {pdf_filename}
- New PDF File ID: {file_id}
- Link: {web_link}"""

    logger.info(f"Presentation exported successfully for {user_google_email}")
    return confirmation_message


# Create comment management tools for slides
_comment_tools = create_comment_tools("presentation", "presentation_id")
read_presentation_comments = _comment_tools["read_comments"]
create_presentation_comment = _comment_tools["create_comment"]
reply_to_presentation_comment = _comment_tools["reply_to_comment"]
resolve_presentation_comment = _comment_tools["resolve_comment"]

# Aliases for backwards compatibility and intuitive naming
read_slide_comments = read_presentation_comments
create_slide_comment = create_presentation_comment
reply_to_slide_comment = reply_to_presentation_comment
resolve_slide_comment = resolve_presentation_comment
