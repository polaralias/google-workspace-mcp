# Tool Reference

This reference is generated from the Google Workspace tool manifests and covers all 121 unique tools exposed by the server.

Parameter format notes:
- `required` means the manifest schema marks the field as mandatory.
- `default ...` only appears when the manifest defines a default value.
- Many tools accept `user_google_email` to select the authenticated user context explicitly.

## Core And Shared Tools

Source manifest: `tool_manifest_google.json`

### `list_calendars`

Retrieves a list of calendars accessible to the authenticated user.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `page_size` | `number` | optional default `100` | The maximum number of calendars to return.
  - `page_token` | `string` | optional | Token for retrieving the next page of results.

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

### `delete_event`

Deletes an existing event.

- Parameters:
  - `user_google_email` | `string` | required
  - `event_id` | `string` | required
  - `calendar_id` | `string` | optional default `primary`

### `list_spaces`

Lists Google Chat spaces.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `page_size` | `number` | optional default `100`
  - `space_type` | `string` | optional default `all`

### `create_space`

Creates a new Chat space.

- Parameters:
  - `user_google_email` | `string` | required
  - `display_name` | `string` | required
  - `space_type` | `string` | optional default `SPACE`
  - `external_user_allowed` | `boolean` | optional default `False`

### `list_members`

List members of a space.

- Parameters:
  - `user_google_email` | `string` | required
  - `space_id` | `string` | required
  - `page_size` | `number` | optional default `100`

### `add_member`

Adds a member to a space.

- Parameters:
  - `user_google_email` | `string` | required
  - `space_id` | `string` | required
  - `member_name` | `string` | required | Resource name like users/12345 or users/email@example.com

### `remove_member`

Remove a member from a space.

- Parameters:
  - `user_google_email` | `string` | required
  - `space_id` | `string` | required
  - `member_name` | `string` | required | Resource name of membership, e.g. spaces/X/members/Y

### `get_messages`

Get messages from a space.

- Parameters:
  - `user_google_email` | `string` | required
  - `space_id` | `string` | required
  - `page_size` | `number` | optional default `50`

### `send_message`

Send a message to a space.

- Parameters:
  - `user_google_email` | `string` | required
  - `space_id` | `string` | required
  - `message_text` | `string` | required
  - `thread_key` | `string` | optional

### `create_doc`

Creates a new Google Doc.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `title` | `string` | required | Document title.
  - `content` | `string` | optional | Initial content.

### `get_doc_content`

Retrieves content of a Google Doc.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `document_id` | `string` | required | Document ID.

### `modify_doc_text`

Inserts or replaces text in a Google Doc.

- Parameters:
  - `user_google_email` | `string` | required
  - `document_id` | `string` | required
  - `text` | `string` | required
  - `index` | `number` | optional default `1`
  - `start_index` | `number` | optional
  - `end_index` | `number` | optional

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

### `get_drive_file_content`

Retrieves the content of a specific Google Drive file.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required

### `create_drive_file`

Creates a new file in Google Drive.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_name` | `string` | required
  - `content` | `string` | optional
  - `folder_id` | `string` | optional default `root`
  - `mime_type` | `string` | optional default `text/plain`

### `get_drive_file_permissions`

Gets detailed metadata including permissions.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required

### `search_gmail_messages`

Searches messages in a user's Gmail account based on a query.

- Parameters:
  - `query` | `string` | required | The search query. Supports standard Gmail search operators.
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `page_size` | `number` | optional default `10` | The maximum number of messages to return.
  - `page_token` | `string` | optional | Token for retrieving the next page of results.

### `get_gmail_message_content`

Retrieves the full content of a specific Gmail message.

- Parameters:
  - `message_id` | `string` | required | The unique ID of the Gmail message to retrieve.
  - `user_google_email` | `string` | required | The user's Google email address. Required.

### `get_gmail_messages_content_batch`

Retrieves content of multiple Gmail messages.

- Parameters:
  - `message_ids` | `array` | required | List of Gmail message IDs to retrieve (max 25).
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `format` | `string` | optional default `full` | Message format.

### `get_gmail_attachment_content`

Downloads the content of a specific email attachment.

- Parameters:
  - `message_id` | `string` | required
  - `attachment_id` | `string` | required
  - `user_google_email` | `string` | required

### `list_spreadsheets`

Lists spreadsheets from Google Drive.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `page_size` | `number` | optional default `25` | Max spreadsheets to return.
  - `page_token` | `string` | optional

### `get_spreadsheet_info`

Gets information about a specific spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `spreadsheet_id` | `string` | required | The ID of the spreadsheet.

### `read_sheet_values`

Reads values from a specific range in a Google Sheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `range_name` | `string` | optional default `A1:Z1000`

### `modify_sheet_values`

Modifies values in a specific range of a Google Sheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `range_name` | `string` | required
  - `values` | `any` | optional
  - `value_input_option` | `string` | optional default `USER_ENTERED`
  - `clear_values` | `boolean` | optional default `False`

### `create_presentation`

Creates a new Google Slide presentation.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `title` | `string` | optional default `Untitled Presentation`

### `get_presentation`

Gets details about a presentation.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `presentation_id` | `string` | required | The ID of the presentation.

### `create_slide`

Creates a new slide.

- Parameters:
  - `user_google_email` | `string` | required
  - `presentation_id` | `string` | required
  - `layout` | `string` | optional default `TITLE_AND_BODY`
  - `insertion_index` | `number` | optional

### `add_textbox`

Adds a textbox to a slide.

- Parameters:
  - `user_google_email` | `string` | required
  - `presentation_id` | `string` | required
  - `page_id` | `string` | required
  - `text` | `string` | required
  - `x` | `number` | required
  - `y` | `number` | required
  - `width` | `number` | required
  - `height` | `number` | required

### `list_task_lists`

List all task lists.

- Parameters:
  - `user_google_email` | `string` | required | The user's Google email address. Required.
  - `max_results` | `number` | optional default `100`
  - `page_token` | `string` | optional

### `create_task_list`

Create a new task list.

- Parameters:
  - `user_google_email` | `string` | required
  - `title` | `string` | required

### `delete_task_list`

Delete a task list.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required

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

### `create_task`

Create a new task.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required
  - `title` | `string` | required
  - `notes` | `string` | optional
  - `due` | `string` | optional | RFC 3339 format
  - `parent` | `string` | optional

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

### `delete_task`

Delete a task.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required
  - `task_id` | `string` | required

### `complete_task`

Mark a task as completed.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required
  - `task_id` | `string` | required

### `clear_completed_tasks`

Clear completed tasks from a list.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required

## Admin, Calendar, Chat, And Docs

Source manifest: `tool_manifest_google_admin_calendar_chat_docs.json`

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

### `create_recurring_event`

Create a recurring Google Calendar event.

- Parameters:
  - `user_google_email` | `string` | required
  - `summary` | `string` | required
  - `start_time` | `string` | required
  - `end_time` | `string` | required
  - `calendar_id` | `string` | optional default `primary`
  - `description` | `string` | optional
  - `location` | `string` | optional
  - `attendees` | `array` | optional
  - `timezone` | `string` | optional
  - `add_google_meet` | `boolean` | optional default `False`
  - `reminders` | `array` | optional
  - `use_default_reminders` | `boolean` | optional default `True`
  - `recurrence` | `any` | required
  - `exceptions` | `array` | optional

### `reply_in_thread`

Reply to a Google Chat thread.

- Parameters:
  - `user_google_email` | `string` | required
  - `space_id` | `string` | required
  - `message_text` | `string` | required
  - `thread_name` | `string` | optional
  - `thread_key` | `string` | optional
  - `message_reply_option` | `string` | optional

### `apply_doc_paragraph_style`

Apply a paragraph style range in a Google Doc.

- Parameters:
  - `user_google_email` | `string` | required
  - `document_id` | `string` | required
  - `start_index` | `number` | required
  - `end_index` | `number` | required
  - `named_style_type` | `string` | optional
  - `alignment` | `string` | optional

### `apply_doc_text_style`

Apply a text style range in a Google Doc.

- Parameters:
  - `user_google_email` | `string` | required
  - `document_id` | `string` | required
  - `start_index` | `number` | required
  - `end_index` | `number` | required
  - `bold` | `boolean` | optional
  - `italic` | `boolean` | optional
  - `underline` | `boolean` | optional
  - `strikethrough` | `boolean` | optional
  - `link_url` | `string` | optional
  - `font_size_pt` | `number` | optional
  - `weighted_font_family` | `string` | optional
  - `foreground_color` | `object` | optional

### `export_doc`

Export a Google Doc as PDF, DOCX, or HTML.

- Parameters:
  - `user_google_email` | `string` | required
  - `document_id` | `string` | required
  - `format` | `string` | optional default `pdf`

## Drive And Gmail

Source manifest: `tool_manifest_google_drive_gmail.json`

### `create_drive_folder`

Create a folder in Google Drive.

- Parameters:
  - `user_google_email` | `string` | required
  - `folder_name` | `string` | required
  - `parent_folder_id` | `string` | optional default `root`

### `copy_drive_file`

Copy a file in Google Drive.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required
  - `name` | `string` | optional
  - `parent_folder_id` | `string` | optional

### `trash_drive_file`

Move a Drive file to trash.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required

### `untrash_drive_file`

Restore a Drive file from trash.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required

### `delete_drive_file`

Delete a Drive file permanently.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required

### `list_drive_revisions`

List revisions for a Drive file.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required
  - `page_size` | `number` | optional default `50`
  - `page_token` | `string` | optional

### `get_drive_revision`

Get a specific Drive file revision.

- Parameters:
  - `user_google_email` | `string` | required
  - `file_id` | `string` | required
  - `revision_id` | `string` | required

### `list_shared_drives`

List shared drives visible to the user.

- Parameters:
  - `user_google_email` | `string` | required
  - `page_size` | `number` | optional default `100`
  - `page_token` | `string` | optional

### `archive_gmail_message`

Archive a Gmail message.

- Parameters:
  - `user_google_email` | `string` | required
  - `message_id` | `string` | required

### `trash_gmail_message`

Move a Gmail message to trash.

- Parameters:
  - `user_google_email` | `string` | required
  - `message_id` | `string` | required

### `mark_gmail_read_unread`

Mark a Gmail message as read or unread.

- Parameters:
  - `user_google_email` | `string` | required
  - `message_id` | `string` | required
  - `mark_read` | `boolean` | optional default `True`

### `star_unstar_gmail_message`

Star or unstar a Gmail message.

- Parameters:
  - `user_google_email` | `string` | required
  - `message_id` | `string` | required
  - `starred` | `boolean` | optional default `True`

### `list_gmail_filters`

List Gmail filters.

- Parameters:
  - `user_google_email` | `string` | required

### `create_gmail_filter`

Create a Gmail filter.

- Parameters:
  - `user_google_email` | `string` | required
  - `criteria` | `object` | required
  - `action` | `object` | required

### `delete_gmail_filter`

Delete a Gmail filter.

- Parameters:
  - `user_google_email` | `string` | required
  - `filter_id` | `string` | required

## Keep, People, Forms, And Meet

Source manifest: `tool_manifest_google_keep_people_forms_meet.json`

### `list_keep_notes`

List Google Keep notes.

- Parameters:
  - `user_google_email` | `string` | required
  - `filter` | `string` | optional
  - `page_size` | `number` | optional default `25`
  - `page_token` | `string` | optional

### `get_keep_note`

Get a Google Keep note.

- Parameters:
  - `user_google_email` | `string` | required
  - `note_name` | `string` | required

### `create_keep_note`

Create a Google Keep note.

- Parameters:
  - `user_google_email` | `string` | required
  - `title` | `string` | required
  - `text` | `string` | optional
  - `list_items` | `array` | optional

### `delete_keep_note`

Delete a Google Keep note.

- Parameters:
  - `user_google_email` | `string` | required
  - `note_name` | `string` | required

### `download_keep_attachment`

Download a Google Keep attachment.

- Parameters:
  - `user_google_email` | `string` | required
  - `attachment_name` | `string` | required
  - `mime_type` | `string` | required

### `share_keep_note`

Share a Google Keep note with writers.

- Parameters:
  - `user_google_email` | `string` | required
  - `note_name` | `string` | required
  - `writers` | `array` | required

### `unshare_keep_note`

Remove sharing from a Google Keep note.

- Parameters:
  - `user_google_email` | `string` | required
  - `note_name` | `string` | required
  - `emails_or_groups` | `array` | required

### `get_keep_note_permissions`

List permissions on a Google Keep note.

- Parameters:
  - `user_google_email` | `string` | required
  - `note_name` | `string` | required

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

### `create_contact`

Create a Google contact.

- Parameters:
  - `user_google_email` | `string` | required
  - `person` | `object` | required
  - `person_fields` | `string` | optional

### `update_contact`

Update a Google contact.

- Parameters:
  - `user_google_email` | `string` | required
  - `resource_name` | `string` | required
  - `person` | `object` | required
  - `update_person_fields` | `string` | optional
  - `person_fields` | `string` | optional

### `delete_contact`

Delete a Google contact.

- Parameters:
  - `user_google_email` | `string` | required
  - `resource_name` | `string` | required

### `batch_update_form`

Apply a batch update to a Google Form.

- Parameters:
  - `user_google_email` | `string` | required
  - `form_id` | `string` | required
  - `requests` | `array` | required
  - `include_form_in_response` | `boolean` | optional default `False`
  - `write_control` | `object` | optional

### `list_conference_records`

List Google Meet conference records.

- Parameters:
  - `user_google_email` | `string` | required
  - `page_size` | `number` | optional default `25`
  - `page_token` | `string` | optional
  - `filter` | `string` | optional

### `get_conference_record`

Get a Google Meet conference record.

- Parameters:
  - `user_google_email` | `string` | required
  - `name` | `string` | required

## Google Keep Master-Token Tools

Source manifest: `tool_manifest_google_keep_unofficial.json`

### `find_keep_notes`

Find Google Keep notes using the unofficial master-token backend with query, label, color, pin, archive, and trash filters.

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

### `create_keep_list`

Create a Google Keep checklist using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `title` | `string` | optional
  - `items` | `array` | optional

### `update_keep_note`

Update a Google Keep note title and/or text using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `title` | `string` | optional
  - `text` | `string` | optional

### `add_keep_list_item`

Add an item to a Google Keep checklist using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `text` | `string` | required
  - `checked` | `boolean` | optional default `False`

### `update_keep_list_item`

Update a Google Keep checklist item using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `item_id` | `string` | required
  - `text` | `string` | optional
  - `checked` | `boolean` | optional

### `delete_keep_list_item`

Delete a Google Keep checklist item using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `item_id` | `string` | required

### `set_keep_note_color`

Set a Google Keep note color using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `color` | `string` | required

### `pin_keep_note`

Pin or unpin a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `pinned` | `boolean` | optional default `True`

### `archive_keep_note`

Archive or unarchive a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `archived` | `boolean` | optional default `True`

### `trash_keep_note`

Move a Google Keep note to trash using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required

### `restore_keep_note`

Restore a trashed Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required

### `list_keep_labels`

List Google Keep labels using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional

### `create_keep_label`

Create a Google Keep label using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `name` | `string` | required

### `delete_keep_label`

Delete a Google Keep label using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `label_id` | `string` | required

### `add_keep_label_to_note`

Add a label to a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `label_id` | `string` | required

### `remove_keep_label_from_note`

Remove a label from a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `label_id` | `string` | required

### `list_keep_note_collaborators`

List Google Keep note collaborators using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required

### `add_keep_note_collaborator`

Add a collaborator to a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `email` | `string` | required

### `remove_keep_note_collaborator`

Remove a collaborator from a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required
  - `email` | `string` | required

### `list_keep_note_media`

List media blobs and direct links for a Google Keep note using the unofficial master-token backend.

- Parameters:
  - `user_google_email` | `string` | optional
  - `note_name` | `string` | required

## Sheets, Slides, And Tasks

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

### `create_named_range`

Create a named range in a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `name` | `string` | required
  - `grid_range` | `object` | required

### `update_named_range`

Update a named range in a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `named_range_id` | `string` | required
  - `name` | `string` | required
  - `grid_range` | `object` | required

### `delete_named_range`

Delete a named range from a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `named_range_id` | `string` | required

### `add_data_validation`

Add a data validation rule to a sheet range.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `grid_range` | `object` | required
  - `rule` | `object` | required
  - `filtered_rows_included` | `boolean` | optional default `False`

### `set_protected_range`

Add a protected range to a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `protected_range` | `object` | required

### `create_chart`

Create a chart in a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `chart` | `object` | optional
  - `chart_spec` | `object` | optional
  - `position` | `object` | optional

### `update_chart`

Update a chart spec in a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `chart_id` | `number` | required
  - `chart_spec` | `object` | required

### `create_pivot_table`

Create a pivot table in a spreadsheet.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `pivot_table` | `object` | required
  - `start` | `object` | optional
  - `sheet_id` | `number` | optional
  - `start_row_index` | `number` | optional
  - `start_column_index` | `number` | optional

### `set_text_style`

Apply text styles inside a Google Slides text box or shape.

- Parameters:
  - `user_google_email` | `string` | required
  - `presentation_id` | `string` | required
  - `object_id` | `string` | required
  - `start_index` | `number` | optional
  - `end_index` | `number` | optional
  - `bold` | `boolean` | optional
  - `italic` | `boolean` | optional
  - `underline` | `boolean` | optional
  - `strikethrough` | `boolean` | optional
  - `link_url` | `string` | optional
  - `font_size_pt` | `number` | optional
  - `foreground_color` | `object` | optional

### `replace_text_everywhere`

Replace text across a presentation.

- Parameters:
  - `user_google_email` | `string` | required
  - `presentation_id` | `string` | required
  - `contains_text` | `string` | required
  - `replace_text` | `string` | required
  - `match_case` | `boolean` | optional default `False`

### `insert_image_from_url`

Insert an image into a Google Slides page from a URL.

- Parameters:
  - `user_google_email` | `string` | required
  - `presentation_id` | `string` | required
  - `page_id` | `string` | required
  - `url` | `string` | required
  - `x` | `number` | required
  - `y` | `number` | required
  - `width` | `number` | required
  - `height` | `number` | required
  - `object_id` | `string` | optional

### `export_presentation_pdf`

Export a Google Slides presentation as PDF.

- Parameters:
  - `user_google_email` | `string` | required
  - `presentation_id` | `string` | required

### `reopen_task`

Reopen a Google Task.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required
  - `task_id` | `string` | required

### `set_task_due_date`

Set the due date for a Google Task.

- Parameters:
  - `user_google_email` | `string` | required
  - `task_list_id` | `string` | required
  - `task_id` | `string` | required
  - `due` | `string` | required

### `format_sheet_range`

Apply user-entered formatting to a sheet range.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `grid_range` | `object` | required
  - `cell_format` | `object` | required

### `add_conditional_formatting`

Add a conditional formatting rule.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `rule` | `object` | required
  - `index` | `number` | optional default `0`

### `update_conditional_formatting`

Update a conditional formatting rule.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `index` | `number` | required
  - `rule` | `object` | required
  - `new_index` | `number` | optional
  - `sheet_id` | `number` | optional

### `delete_conditional_formatting`

Delete a conditional formatting rule.

- Parameters:
  - `user_google_email` | `string` | required
  - `spreadsheet_id` | `string` | required
  - `sheet_id` | `number` | required
  - `index` | `number` | required
