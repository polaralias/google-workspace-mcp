from __future__ import annotations

import json
from typing import Any, Callable


SHEETS_TOOL_NAMES = {
    "list_spreadsheets",
    "get_spreadsheet_info",
    "read_sheet_values",
    "modify_sheet_values",
    "append_sheet_rows",
    "batch_get_sheet_values",
    "batch_update_sheet_values",
    "create_named_range",
    "update_named_range",
    "delete_named_range",
    "add_data_validation",
    "set_protected_range",
    "create_chart",
    "update_chart",
    "create_pivot_table",
    "format_sheet_range",
    "add_conditional_formatting",
    "update_conditional_formatting",
    "delete_conditional_formatting",
}


async def dispatch_sheets(
    runtime: Any,
    user_email: str | None,
    name: str,
    args: dict[str, Any],
    *,
    as_list: Callable[[Any, str], list[Any]],
    as_string_list: Callable[[Any, str], list[str]],
    as_dict: Callable[[Any, str], dict[str, Any]],
    grid_range: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    if name == "list_spreadsheets":
        svc = runtime._svc(user_email, "drive", "v3")
        data = svc.files().list(q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false", pageSize=args.get("page_size", 25), pageToken=args.get("page_token"), fields="nextPageToken, files(id,name,modifiedTime,webViewLink)", orderBy="modifiedTime desc", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        return {"spreadsheets": data.get("files", []), "nextPageToken": data.get("nextPageToken")}
    svc = runtime._svc(user_email, "sheets", "v4")
    if name == "get_spreadsheet_info":
        data = svc.spreadsheets().get(spreadsheetId=args["spreadsheet_id"], fields="spreadsheetId,properties(title,locale),sheets(properties(title,sheetId,gridProperties(rowCount,columnCount)))").execute()
        return {"spreadsheet": data}
    if name == "read_sheet_values":
        data = svc.spreadsheets().values().get(spreadsheetId=args["spreadsheet_id"], range=args.get("range_name", "A1:Z1000")).execute()
        return {"range": data.get("range"), "values": data.get("values", [])}
    if name == "modify_sheet_values":
        if args.get("clear_values"):
            data = svc.spreadsheets().values().clear(spreadsheetId=args["spreadsheet_id"], range=args["range_name"], body={}).execute()
            return {"cleared": True, "result": data}
        values = args.get("values")
        if isinstance(values, str):
            values = json.loads(values)
        if not isinstance(values, list):
            raise ValueError("values must be a 2D array")
        data = svc.spreadsheets().values().update(spreadsheetId=args["spreadsheet_id"], range=args["range_name"], valueInputOption=args.get("value_input_option", "USER_ENTERED"), body={"values": values}).execute()
        return {"updated": True, "result": data}
    if name == "append_sheet_rows":
        values = as_list(args.get("values"), "values") if isinstance(args.get("values"), str) else args.get("values")
        if not isinstance(values, list):
            raise ValueError("values must be a 2D array")
        data = svc.spreadsheets().values().append(spreadsheetId=args["spreadsheet_id"], range=args["range_name"], valueInputOption=args.get("value_input_option", "USER_ENTERED"), insertDataOption=args.get("insert_data_option", "INSERT_ROWS"), body={"values": values}).execute()
        return {"appended": True, "result": data}
    if name == "batch_get_sheet_values":
        ranges = as_string_list(args.get("ranges"), "ranges")
        if not ranges:
            raise ValueError("ranges is required")
        data = svc.spreadsheets().values().batchGet(spreadsheetId=args["spreadsheet_id"], ranges=ranges, majorDimension=args.get("major_dimension")).execute()
        return {"valueRanges": data.get("valueRanges", [])}
    if name == "batch_update_sheet_values":
        data_items = as_list(args.get("data"), "data") if isinstance(args.get("data"), str) else args.get("data")
        if not isinstance(data_items, list):
            raise ValueError("data must be a list")
        data = svc.spreadsheets().values().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"valueInputOption": args.get("value_input_option", "USER_ENTERED"), "includeValuesInResponse": args.get("include_values_in_response", False), "data": data_items}).execute()
        return {"updated": True, "result": data}
    if name == "create_named_range":
        named_range = {"name": args["name"], "range": grid_range(args.get("grid_range"))}
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"addNamedRange": {"namedRange": named_range}}]}).execute()
        return {"created": True, "result": data}
    if name == "update_named_range":
        named_range = {"namedRangeId": args["named_range_id"], "name": args["name"], "range": grid_range(args.get("grid_range"))}
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"updateNamedRange": {"namedRange": named_range, "fields": "name,range"}}]}).execute()
        return {"updated": True, "result": data}
    if name == "delete_named_range":
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"deleteNamedRange": {"namedRangeId": args["named_range_id"]}}]}).execute()
        return {"deleted": True, "result": data}
    if name == "add_data_validation":
        rule = as_dict(args.get("rule"), "rule")
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"setDataValidation": {"range": grid_range(args.get("grid_range")), "rule": rule, "filteredRowsIncluded": args.get("filtered_rows_included", False)}}]}).execute()
        return {"updated": True, "result": data}
    if name == "set_protected_range":
        protected_range = as_dict(args.get("protected_range"), "protected_range")
        if not protected_range:
            raise ValueError("protected_range is required")
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"addProtectedRange": {"protectedRange": protected_range}}]}).execute()
        return {"created": True, "result": data}
    if name == "create_chart":
        chart = as_dict(args.get("chart"), "chart")
        if not chart:
            spec = as_dict(args.get("chart_spec"), "chart_spec")
            if not spec:
                raise ValueError("chart or chart_spec is required")
            chart = {"spec": spec}
            position = as_dict(args.get("position"), "position")
            if position:
                chart["position"] = position
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"addChart": {"chart": chart}}]}).execute()
        return {"created": True, "result": data}
    if name == "update_chart":
        spec = as_dict(args.get("chart_spec"), "chart_spec")
        if not spec:
            raise ValueError("chart_spec is required")
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"updateChartSpec": {"chartId": int(args["chart_id"]), "spec": spec}}]}).execute()
        return {"updated": True, "result": data}
    if name == "create_pivot_table":
        pivot_table = as_dict(args.get("pivot_table"), "pivot_table")
        if not pivot_table:
            raise ValueError("pivot_table is required")
        start = as_dict(args.get("start"), "start")
        if not start:
            start = {"sheetId": int(args["sheet_id"]), "rowIndex": int(args.get("start_row_index", 0)), "columnIndex": int(args.get("start_column_index", 0))}
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"updateCells": {"start": start, "rows": [{"values": [{"pivotTable": pivot_table}]}], "fields": "pivotTable"}}]}).execute()
        return {"created": True, "result": data}
    if name == "format_sheet_range":
        cell_format = as_dict(args.get("cell_format"), "cell_format")
        if not cell_format:
            raise ValueError("cell_format is required")
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"repeatCell": {"range": grid_range(args.get("grid_range")), "cell": {"userEnteredFormat": cell_format}, "fields": "userEnteredFormat"}}]}).execute()
        return {"updated": True, "result": data}
    if name == "add_conditional_formatting":
        rule = as_dict(args.get("rule"), "rule")
        if not rule:
            raise ValueError("rule is required")
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"addConditionalFormatRule": {"rule": rule, "index": int(args.get("index", 0))}}]}).execute()
        return {"created": True, "result": data}
    if name == "update_conditional_formatting":
        rule = as_dict(args.get("rule"), "rule")
        if not rule:
            raise ValueError("rule is required")
        request: dict[str, Any] = {"index": int(args["index"]), "rule": rule}
        if args.get("new_index") is not None:
            request["newIndex"] = int(args["new_index"])
        if args.get("sheet_id") is not None:
            request["sheetId"] = int(args["sheet_id"])
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"updateConditionalFormatRule": request}]}).execute()
        return {"updated": True, "result": data}
    if name == "delete_conditional_formatting":
        request = {"sheetId": int(args["sheet_id"]), "index": int(args["index"])}
        data = svc.spreadsheets().batchUpdate(spreadsheetId=args["spreadsheet_id"], body={"requests": [{"deleteConditionalFormatRule": request}]}).execute()
        return {"deleted": True, "result": data}
    raise NotImplementedError(f"Tool '{name}' is not implemented for Sheets")
