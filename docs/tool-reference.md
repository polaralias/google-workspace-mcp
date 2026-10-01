---
type: "Reference"
title: "Tool Reference"
description: "Documents Tool Reference for the google-workspace-mcp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - google-workspace-mcp
  - reference
navigation:
  role: reference
  order: 200
---
# Tool Reference

This reference is generated from the public Google Workspace tool manifests and covers all 69 unique tools exposed by the server.

Parameter format notes:
- `required` means the manifest schema marks the field as mandatory.
- `default ...` only appears when the manifest defines a default value.
- Many tools accept `user_google_email` to select the authenticated user context explicitly.

## `tool_manifest_google.json`

Source manifest: `tool_manifest_google.json`

### `create_doc`

Creates a new Google Doc.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `title` | `string` | required | Document title.
- `content` | `string` | optional | Initial content.

### `create_drive_file`

Creates a new file in Google Drive.

- Parameters:
- `user_google_email` | `string` | required
- `file_name` | `string` | required
- `content` | `string` | optional
- `folder_id` | `string` | optional default `root`
- `mime_type` | `string` | optional default `text/plain`

### `create_event`

Creates a new event.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `summary` | `string` | required | Event title.
- `start_time` | `string` | required | Start time (RFC3339).
- `end_time` | `string` | required | End time (RFC3339).
- `calendar_id` | `string` | optional default `primary`
- `description` | `string` | optional
- `location` | `string` | optional
- `attendees` | `array` | optional
- `timezone` | `string` | optional
- `add_google_meet` | `boolean` | optional default `False`
- `reminders` | `any` | optional
- `use_default_reminders` | `boolean` | optional default `True`

### `create_presentation`

Creates a new Google Slide presentation.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `title` | `string` | optional default `Untitled Presentation`

### `create_slide`

Creates a new slide.

- Parameters:
- `user_google_email` | `string` | required
- `presentation_id` | `string` | required
- `layout` | `string` | optional default `TITLE_AND_BODY`
- `insertion_index` | `number` | optional

### `create_task`

Create a new task.

- Parameters:
- `user_google_email` | `string` | required
- `task_list_id` | `string` | required
- `title` | `string` | required
- `notes` | `string` | optional
- `due` | `string` | optional | RFC 3339 format
- `parent` | `string` | optional

### `create_task_list`

Create a new task list.

- Parameters:
- `user_google_email` | `string` | required
- `title` | `string` | required

### `delete_event`

Deletes an existing event.

- Parameters:
- `user_google_email` | `string` | required
- `event_id` | `string` | required
- `calendar_id` | `string` | optional default `primary`

### `delete_task`

Delete a task.

- Parameters:
- `user_google_email` | `string` | required
- `task_list_id` | `string` | required
- `task_id` | `string` | required

### `delete_task_list`

Delete a task list.

- Parameters:
- `user_google_email` | `string` | required
- `task_list_id` | `string` | required

### `get_doc_content`

Retrieves content of a Google Doc.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `document_id` | `string` | required | Document ID.

### `get_drive_file_content`

Retrieves the content of a specific Google Drive file.

- Parameters:
- `user_google_email` | `string` | required
- `file_id` | `string` | required

### `get_drive_file_permissions`

Gets detailed metadata including permissions.

- Parameters:
- `user_google_email` | `string` | required
- `file_id` | `string` | required

### `get_events`

Retrieves events from a specified Google Calendar.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `calendar_id` | `string` | optional default `primary` | The ID of the calendar to query.
- `event_id` | `string` | optional | The ID of a specific event to retrieve.
- `time_min` | `string` | optional | The start of the time range (inclusive) in RFC3339 format.
- `time_max` | `string` | optional | The end of the time range (exclusive) in RFC3339 format.
- `page_size` | `number` | optional default `25` | Max events to return.
- `page_token` | `string` | optional
- `query` | `string` | optional | Text search query.
- `detailed` | `boolean` | optional default `False` | Return detailed info.
- `include_attachments` | `boolean` | optional default `False` | Include attachments in detailed output.

### `get_presentation`

Gets details about a presentation.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `presentation_id` | `string` | required | The ID of the presentation.

### `get_spreadsheet_info`

Gets information about a specific spreadsheet.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `spreadsheet_id` | `string` | required | The ID of the spreadsheet.

### `list_calendars`

Retrieves a list of calendars accessible to the authenticated user.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `page_size` | `number` | optional default `100` | The maximum number of calendars to return.
- `page_token` | `string` | optional | Token for retrieving the next page of results.

### `list_drive_items`

Lists files and folders, supporting shared drives.

- Parameters:
- `user_google_email` | `string` | required
- `folder_id` | `string` | optional default `root`
- `page_size` | `number` | optional default `100`
- `page_token` | `string` | optional
- `drive_id` | `string` | optional
- `include_items_from_all_drives` | `boolean` | optional default `True`
- `corpora` | `string` | optional

### `list_task_lists`

List all task lists.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `max_results` | `number` | optional default `100`
- `page_token` | `string` | optional

### `list_tasks`

List tasks in a task list.

- Parameters:
- `user_google_email` | `string` | required
- `task_list_id` | `string` | required
- `max_results` | `number` | optional default `20`
- `page_token` | `string` | optional
- `show_completed` | `boolean` | optional default `True`
- `show_deleted` | `boolean` | optional default `False`
- `show_hidden` | `boolean` | optional default `False`

### `modify_doc_text`

Inserts or replaces text in a Google Doc.

- Parameters:
- `user_google_email` | `string` | required
- `document_id` | `string` | required
- `text` | `string` | required
- `index` | `number` | optional default `1`
- `start_index` | `number` | optional
- `end_index` | `number` | optional

### `modify_sheet_values`

Modifies values in a specific range of a Google Sheet.

- Parameters:
- `user_google_email` | `string` | required
- `spreadsheet_id` | `string` | required
- `range_name` | `string` | required
- `values` | `any` | optional
- `value_input_option` | `string` | optional default `USER_ENTERED`
- `clear_values` | `boolean` | optional default `False`

### `read_sheet_values`

Reads values from a specific range in a Google Sheet.

- Parameters:
- `user_google_email` | `string` | required
- `spreadsheet_id` | `string` | required
- `range_name` | `string` | optional default `A1:Z1000`

### `search_drive_files`

Searches for files and folders within a user's Google Drive.

- Parameters:
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `query` | `string` | required | The search query string.
- `page_size` | `number` | optional default `10` | Max files to return.
- `page_token` | `string` | optional
- `drive_id` | `string` | optional
- `include_items_from_all_drives` | `boolean` | optional default `True`
- `corpora` | `string` | optional

### `search_gmail_messages`

Searches messages in a user's Gmail account based on a query.

- Parameters:
- `query` | `string` | required | The search query. Supports standard Gmail search operators.
- `user_google_email` | `string` | required | The user's Google email address. Required.
- `page_size` | `number` | optional default `10` | The maximum number of messages to return.
- `page_token` | `string` | optional | Token for retrieving the next page of results.

### `update_task`

Update a task.

- Parameters:
- `user_google_email` | `string` | required
- `task_list_id` | `string` | required
- `task_id` | `string` | required
- `title` | `string` | optional
- `notes` | `string` | optional
- `status` | `string` | optional
- `due` | `string` | optional

## `tool_manifest_google_admin_calendar_chat_docs.json`

Source manifest: `tool_manifest_google_admin_calendar_chat_docs.json`

### `create_calendar_acl_rule`

Create an ACL rule on a calendar.

- Parameters:
- `user_google_email` | `string` | required
- `calendar_id` | `string` | optional default `primary`
- `role` | `string` | required
- `scope_type` | `string` | required
- `scope_value` | `string` | required
- `send_notifications` | `boolean` | optional default `False`

### `delete_calendar_acl_rule`

Delete an ACL rule from a calendar.

- Parameters:
- `user_google_email` | `string` | required
- `calendar_id` | `string` | optional default `primary`
- `rule_id` | `string` | required

### `get_free_busy`

Query Google Calendar free/busy information.

- Parameters:
- `user_google_email` | `string` | required
- `time_min` | `string` | required
- `time_max` | `string` | required
- `items` | `array` | required
- `time_zone` | `string` | optional

### `list_calendar_acl`

List ACL rules on a calendar.

- Parameters:
- `user_google_email` | `string` | required
- `calendar_id` | `string` | optional default `primary`
- `page_size` | `number` | optional default `100`
- `page_token` | `string` | optional
- `show_deleted` | `boolean` | optional default `False`

## `tool_manifest_google_drive_gmail.json`

Source manifest: `tool_manifest_google_drive_gmail.json`

### `create_drive_folder`

Create a folder in Google Drive.

- Parameters:
- `user_google_email` | `string` | required
- `folder_name` | `string` | required
- `parent_folder_id` | `string` | optional default `root`

### `create_gmail_filter`

Create a Gmail filter.

- Parameters:
- `user_google_email` | `string` | required
- `criteria` | `object` | required
- `action` | `object` | required

### `delete_drive_file`

Delete a Drive file permanently.

- Parameters:
- `user_google_email` | `string` | required
- `file_id` | `string` | required

### `delete_gmail_filter`

Delete a Gmail filter.

- Parameters:
- `user_google_email` | `string` | required
- `filter_id` | `string` | required

### `list_gmail_filters`

List Gmail filters.

- Parameters:
- `user_google_email` | `string` | required

## `tool_manifest_google_health.json`

Source manifest: `tool_manifest_google_health.json`

### `health_catalog`

List the 43 documented Google Health data types, allowed operations, and required OAuth scopes.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.

### `health_create_data_point`

Create a Google Health record where the selected data type supports create. Use nutrition-log for calories consumed and exercise for workout sessions.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `body` | `object` | required | Google Health API v4 request body for this operation.

### `health_daily_rollup_data_points`

Aggregate Google Health records by day using a v4 DailyRollUpDataPointsRequest body.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `body` | `object` | required | Google Health API v4 request body for this operation.

### `health_delete_data_points`

Delete 1 to 100 records of one Google Health data type owned by the OAuth client.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `point_ids` | `array` | required

### `health_export_exercise_tcx`

Export one exercise record as TCX, capped at 1 MB.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required
- `point_id` | `string` | required | The final ID segment of a users/me/dataTypes/{data_type}/dataPoints/{point_id} resource.
- `partial_data` | `boolean` | optional default `False`

### `health_get_data_point`

Read one Google Health record by data type and point ID.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `point_id` | `string` | required | The final ID segment of a users/me/dataTypes/{data_type}/dataPoints/{point_id} resource.

### `health_get_identity`

Read the Google Health user identity.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.

### `health_get_irn_profile`

Read the Google Health irregular rhythm notification profile.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.

### `health_get_profile`

Read the Google Health user profile.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.

### `health_get_settings`

Read the Google Health user settings.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.

### `health_list_data_points`

List Google Health records for a documented data type. Use page_token for the next page.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `filter` | `string` | optional
- `page_size` | `integer` | optional default `25`
- `page_token` | `string` | optional
- `data_source_family` | `string` | optional

### `health_reconcile_data_points`

Reconcile Google Health records where the data type supports reconciliation.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `filter` | `string` | optional
- `data_source_family` | `string` | optional

### `health_rollup_data_points`

Aggregate Google Health records using a v4 RollUpDataPointsRequest body.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `body` | `object` | required | Google Health API v4 request body for this operation.

### `health_update_data_point`

Update a Google Health record owned by the OAuth client where the data type supports update.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `data_type` | `string` | required | One of the dataType IDs returned by health_catalog.
- `point_id` | `string` | required | The final ID segment of a users/me/dataTypes/{data_type}/dataPoints/{point_id} resource.
- `body` | `object` | required | Google Health API v4 request body for this operation.

### `health_update_profile`

Update the Google Health user profile using an update mask.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `body` | `object` | required | Google Health API v4 request body for this operation.
- `update_mask` | `string` | optional

### `health_update_settings`

Update the Google Health user settings using an update mask.

- Parameters:
- `user_google_email` | `string` | optional | Google account with stored Health OAuth consent; defaults to GOOGLE_DEFAULT_USER_EMAIL.
- `body` | `object` | required | Google Health API v4 request body for this operation.
- `update_mask` | `string` | optional

## `tool_manifest_google_keep_people_forms_meet.json`

Source manifest: `tool_manifest_google_keep_people_forms_meet.json`

### `batch_update_form`

Apply a batch update to a Google Form.

- Parameters:
- `user_google_email` | `string` | required
- `form_id` | `string` | required
- `requests` | `array` | required
- `include_form_in_response` | `boolean` | optional default `False`
- `write_control` | `object` | optional

### `create_contact`

Create a Google contact.

- Parameters:
- `user_google_email` | `string` | required
- `person` | `object` | required
- `person_fields` | `string` | optional

### `delete_contact`

Delete a Google contact.

- Parameters:
- `user_google_email` | `string` | required
- `resource_name` | `string` | required

### `get_conference_record`

Get a Google Meet conference record.

- Parameters:
- `user_google_email` | `string` | required
- `name` | `string` | required

### `list_conference_records`

List Google Meet conference records.

- Parameters:
- `user_google_email` | `string` | required
- `page_size` | `number` | optional default `25`
- `page_token` | `string` | optional
- `filter` | `string` | optional

### `list_contacts`

List Google contacts.

- Parameters:
- `user_google_email` | `string` | required
- `person_fields` | `string` | optional
- `page_size` | `number` | optional default `100`
- `page_token` | `string` | optional
- `sort_order` | `string` | optional
- `sync_token` | `string` | optional

### `search_contacts`

Search Google contacts.

- Parameters:
- `user_google_email` | `string` | required
- `query` | `string` | required
- `page_size` | `number` | optional default `10`
- `read_mask` | `string` | optional
- `sources` | `array` | optional

### `update_contact`

Update a Google contact.

- Parameters:
- `user_google_email` | `string` | required
- `resource_name` | `string` | required
- `person` | `object` | required
- `update_person_fields` | `string` | optional
- `person_fields` | `string` | optional

## `tool_manifest_google_keep_unofficial.json`

Source manifest: `tool_manifest_google_keep_unofficial.json`

### `create_keep_note`

Create a Google Keep note using the unofficial master-token backend.

- Parameters:
- `user_google_email` | `string` | optional
- `title` | `string` | optional
- `text` | `string` | optional
- `list_items` | `array` | optional

### `delete_keep_note`

Delete a Google Keep note using the unofficial master-token backend.

- Parameters:
- `user_google_email` | `string` | optional
- `note_name` | `string` | required

### `get_keep_note`

Get a Google Keep note using the unofficial master-token backend.

- Parameters:
- `user_google_email` | `string` | optional
- `note_name` | `string` | required

### `list_keep_labels`

List Google Keep labels using the unofficial master-token backend.

- Parameters:
- `user_google_email` | `string` | optional

### `list_keep_notes`

List Google Keep notes using the unofficial master-token backend.

- Parameters:
- `user_google_email` | `string` | optional
- `query` | `string` | optional
- `labels` | `array` | optional
- `colors` | `array` | optional
- `pinned` | `boolean` | optional
- `archived` | `boolean` | optional default `False`
- `trashed` | `boolean` | optional default `False`
- `page_size` | `number` | optional default `25`
- `page_token` | `string` | optional

### `update_keep_note`

Update a Google Keep note title and/or text using the unofficial master-token backend.

- Parameters:
- `user_google_email` | `string` | optional
- `note_name` | `string` | required
- `title` | `string` | optional
- `text` | `string` | optional

## `tool_manifest_google_sheets_slides_tasks.json`

Source manifest: `tool_manifest_google_sheets_slides_tasks.json`

### `append_sheet_rows`

Append rows to a Google Sheet.

- Parameters:
- `user_google_email` | `string` | required
- `spreadsheet_id` | `string` | required
- `range_name` | `string` | required
- `values` | `array` | required
- `value_input_option` | `string` | optional default `USER_ENTERED`
- `insert_data_option` | `string` | optional default `INSERT_ROWS`

### `batch_get_sheet_values`

Read multiple ranges from a Google Sheet.

- Parameters:
- `user_google_email` | `string` | required
- `spreadsheet_id` | `string` | required
- `ranges` | `array` | required
- `major_dimension` | `string` | optional

### `batch_update_sheet_values`

Update multiple ranges in a Google Sheet.

- Parameters:
- `user_google_email` | `string` | required
- `spreadsheet_id` | `string` | required
- `data` | `array` | required
- `value_input_option` | `string` | optional default `USER_ENTERED`
- `include_values_in_response` | `boolean` | optional default `False`

### `export_presentation_pdf`

Export a Google Slides presentation as PDF.

- Parameters:
- `user_google_email` | `string` | required
- `presentation_id` | `string` | required

## Repository knowledge

- [Documentation map](knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
