from __future__ import annotations

from typing import Any, Callable


DOCS_TOOL_NAMES = {
    "create_doc",
    "get_doc_content",
    "modify_doc_text",
    "apply_doc_paragraph_style",
    "apply_doc_text_style",
    "export_doc",
}


async def dispatch_docs(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    json_export: Callable[[Any, str], dict[str, Any]],
    extract_doc_text: Callable[[list[dict[str, Any]] | None], str],
    docs_range: Callable[[Any, Any], dict[str, int]],
    field_mask: Callable[..., str],
    optional_color: Callable[[Any, str], dict[str, Any] | None],
) -> dict[str, Any]:
    if name == "export_doc":
        drive = runtime._svc(user_email, "drive", "v3")
        export_formats = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "html": "text/html",
        }
        export_format = str(args.get("format", "pdf")).lower()
        if export_format not in export_formats:
            raise ValueError("format must be one of: pdf, docx, html")
        raw = drive.files().export(fileId=args["document_id"], mimeType=export_formats[export_format]).execute()
        return {"documentId": args["document_id"], **json_export(raw, export_formats[export_format])}

    svc = runtime._svc(user_email, "docs", "v1")
    if name == "create_doc":
        data = svc.documents().create(body={"title": args["title"]}).execute()
        if args.get("content") and data.get("documentId"):
            svc.documents().batchUpdate(
                documentId=data["documentId"],
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": args["content"]}}]},
            ).execute()
        return {"created": True, "document": data}
    if name == "get_doc_content":
        data = svc.documents().get(documentId=args["document_id"]).execute()
        return {"document": data, "text": extract_doc_text((data.get("body") or {}).get("content"))}
    if name == "modify_doc_text":
        reqs: list[dict[str, Any]] = []
        if args.get("start_index") is not None and args.get("end_index") is not None:
            reqs.append({"deleteContentRange": {"range": {"startIndex": int(args["start_index"]), "endIndex": int(args["end_index"])}}})
            reqs.append({"insertText": {"location": {"index": int(args["start_index"])}, "text": args["text"]}})
        else:
            reqs.append({"insertText": {"location": {"index": int(args.get("index", 1))}, "text": args["text"]}})
        data = svc.documents().batchUpdate(documentId=args["document_id"], body={"requests": reqs}).execute()
        return {"updated": True, "result": data}
    if name == "apply_doc_paragraph_style":
        style: dict[str, Any] = {}
        fields: list[str] = []
        if args.get("named_style_type"):
            style["namedStyleType"] = args["named_style_type"]
            fields.append("namedStyleType")
        if args.get("alignment"):
            style["alignment"] = args["alignment"]
            fields.append("alignment")
        if not fields:
            raise ValueError("At least one paragraph style field is required")
        data = svc.documents().batchUpdate(
            documentId=args["document_id"],
            body={"requests": [{"updateParagraphStyle": {"range": docs_range(args.get("start_index"), args.get("end_index")), "paragraphStyle": style, "fields": field_mask(*fields)}}]},
        ).execute()
        return {"updated": True, "result": data}
    style = {}
    fields = []
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
    if args.get("weighted_font_family"):
        style["weightedFontFamily"] = {"fontFamily": args["weighted_font_family"]}
        fields.append("weightedFontFamily")
    color = optional_color(args.get("foreground_color"), "foreground_color")
    if color:
        style["foregroundColor"] = color
        fields.append("foregroundColor")
    if not fields:
        raise ValueError("At least one text style field is required")
    data = svc.documents().batchUpdate(
        documentId=args["document_id"],
        body={"requests": [{"updateTextStyle": {"range": docs_range(args.get("start_index"), args.get("end_index")), "textStyle": style, "fields": field_mask(*fields)}}]},
    ).execute()
    return {"updated": True, "result": data}
