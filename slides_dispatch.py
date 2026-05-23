from __future__ import annotations

import secrets
from typing import Any, Callable


SLIDES_TOOL_NAMES = {
    "create_presentation",
    "get_presentation",
    "create_slide",
    "add_textbox",
    "set_text_style",
    "replace_text_everywhere",
    "insert_image_from_url",
    "export_presentation_pdf",
}


async def dispatch_slides(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    json_export: Callable[[Any, str], dict[str, Any]],
    extract_slide_text: Callable[[dict[str, Any]], str],
    slides_text_range: Callable[[Any, Any], dict[str, Any]],
    field_mask: Callable[..., str],
    optional_color: Callable[[Any, str], dict[str, Any] | None],
) -> dict[str, Any]:
    if name == "export_presentation_pdf":
        drive = runtime._svc(user_email, "drive", "v3")
        raw = drive.files().export(fileId=args["presentation_id"], mimeType="application/pdf").execute()
        return {"presentationId": args["presentation_id"], **json_export(raw, "application/pdf")}
    svc = runtime._svc(user_email, "slides", "v1")
    if name == "create_presentation":
        data = svc.presentations().create(body={"title": args.get("title", "Untitled Presentation")}).execute()
        return {"created": True, "presentation": data}
    if name == "get_presentation":
        data = svc.presentations().get(presentationId=args["presentation_id"]).execute()
        return {"presentation": data, "slides": [{"slideId": s.get("objectId"), "text": extract_slide_text(s)} for s in data.get("slides", [])]}
    if name == "create_slide":
        req: dict[str, Any] = {"createSlide": {"slideLayoutReference": {"predefinedLayout": args.get("layout", "TITLE_AND_BODY")}}}
        if args.get("insertion_index") is not None:
            req["createSlide"]["insertionIndex"] = int(args["insertion_index"])
        data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": [req]}).execute()
        return {"created": True, "result": data}
    if name == "add_textbox":
        object_id = f"textbox_{secrets.token_hex(4)}"
        reqs = [{"createShape": {"objectId": object_id, "shapeType": "TEXT_BOX", "elementProperties": {"pageObjectId": args["page_id"], "size": {"width": {"magnitude": float(args["width"]), "unit": "PT"}, "height": {"magnitude": float(args["height"]), "unit": "PT"}}, "transform": {"scaleX": 1, "scaleY": 1, "translateX": float(args["x"]), "translateY": float(args["y"]), "unit": "PT"}}}}, {"insertText": {"objectId": object_id, "text": args["text"]}}]
        data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": reqs}).execute()
        return {"created": True, "elementId": object_id, "result": data}
    if name == "set_text_style":
        style: dict[str, Any] = {}
        fields: list[str] = []
        for key in ("bold", "italic", "underline", "strikethrough"):
            if args.get(key) is not None:
                style[key] = bool(args[key])
                fields.append(key)
        if args.get("link_url"):
            style["link"] = {"url": args["link_url"]}
            fields.append("link")
        if args.get("font_size_pt") is not None:
            style["fontSize"] = {"magnitude": float(args["font_size_pt"]), "unit": "PT"}
            fields.append("fontSize")
        color = optional_color(args.get("foreground_color"), "foreground_color")
        if color:
            style["foregroundColor"] = color
            fields.append("foregroundColor")
        if not fields:
            raise ValueError("At least one style field is required")
        data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": [{"updateTextStyle": {"objectId": args["object_id"], "textRange": slides_text_range(args.get("start_index"), args.get("end_index")), "style": style, "fields": field_mask(*fields)}}]}).execute()
        return {"updated": True, "result": data}
    if name == "replace_text_everywhere":
        data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": [{"replaceAllText": {"containsText": {"text": args["contains_text"], "matchCase": args.get("match_case", False)}, "replaceText": args["replace_text"]}}]}).execute()
        return {"updated": True, "result": data}
    object_id = str(args.get("object_id") or f"image_{secrets.token_hex(4)}")
    req = {"createImage": {"objectId": object_id, "url": args["url"], "elementProperties": {"pageObjectId": args["page_id"], "size": {"width": {"magnitude": float(args["width"]), "unit": "PT"}, "height": {"magnitude": float(args["height"]), "unit": "PT"}}, "transform": {"scaleX": 1, "scaleY": 1, "translateX": float(args["x"]), "translateY": float(args["y"]), "unit": "PT"}}}}
    data = svc.presentations().batchUpdate(presentationId=args["presentation_id"], body={"requests": [req]}).execute()
    return {"created": True, "objectId": object_id, "result": data}
