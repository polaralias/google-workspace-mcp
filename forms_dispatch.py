from __future__ import annotations

from typing import Any, Callable


FORMS_TOOL_NAMES = {"batch_update_form"}


async def dispatch_forms(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    as_list: Callable[[Any, str], list[Any]],
    as_dict: Callable[[Any, str], dict[str, Any]],
) -> dict[str, Any]:
    svc = runtime._svc(user_email, "forms", "v1")
    body: dict[str, Any] = {"requests": as_list(args.get("requests"), "requests") if isinstance(args.get("requests"), str) else args.get("requests")}
    if not isinstance(body["requests"], list):
        raise ValueError("requests must be a list")
    if args.get("include_form_in_response") is not None:
        body["includeFormInResponse"] = bool(args["include_form_in_response"])
    write_control = as_dict(args.get("write_control"), "write_control")
    if write_control:
        body["writeControl"] = write_control
    data = svc.forms().batchUpdate(formId=args["form_id"], body=body).execute()
    return {"updated": True, "result": data}
