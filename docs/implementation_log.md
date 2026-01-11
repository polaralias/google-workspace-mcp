# Implementation Log

This document tracks the progress of the Google Workspace MCP server implementation.

## Phase 0: Repo alignment fixes (quick wins)

### 0.1 Fix tier config gaps (tools implemented but not reachable in tier mode)
- [x] Updated `core/tool_tiers.yaml` to include missing Gmail and Sheets tools.
    - Gmail: Added `list_gmail_filters` to core tier; `create_gmail_filter`, `delete_gmail_filter` to extended tier.
    - Sheets: Added `format_sheet_range` to core tier; `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting` to extended tier.

### 0.2 Add enablement links for new APIs you’ll introduce
- [x] Updated `core/api_enablement.py` with enablement links and service mappings for:
    - Google Keep (`keep.googleapis.com`)
    - Google People (`people.googleapis.com`)
    - Google Meet (`meet.googleapis.com`)
    - Google Admin SDK (`admin.googleapis.com`)

## Phase 1: Add Google Keep (new app surface)

### 1.1 - 1.4 Implement Google Keep Tools
- [x] Added `gkeep/keep_tools.py` with the following tools:
    - Core: `list_keep_notes`, `get_keep_note`, `create_keep_note`
    - Extended: `delete_keep_note`, `download_keep_attachment`, `share_keep_note`, `unshare_keep_note`
    - Complete: `get_keep_note_permissions`
- [x] Updated `auth/scopes.py` with `https://www.googleapis.com/auth/keep` and `https://www.googleapis.com/auth/keep.readonly`.
- [x] Updated `auth/service_decorator.py` to support `keep` service configuration and scopes.
- [x] Registered `keep` tool in `main.py` (imports, icons, CLI arguments).
- [x] Added `keep` tool tiers to `core/tool_tiers.yaml`.

## Phase 2: Expand existing apps (deepen function coverage)

### 2.1 Gmail
- [x] Added message lifecycle helpers to `gmail/gmail_tools.py`:
    - `archive_gmail_message`
    - `trash_gmail_message`
    - `mark_gmail_read_unread`
    - `star_unstar_gmail_message`
- [x] Updated `core/tool_tiers.yaml` to include these new tools in the `extended` tier for Gmail.

### 2.2 Drive
- [x] Added file lifecycle tools to `gdrive/drive_tools.py`:
    - `create_drive_folder`
    - `copy_drive_file`
    - `trash_drive_file`
    - `untrash_drive_file`
    - `delete_drive_file`
- [x] Added revision tools to `gdrive/drive_tools.py`:
    - `list_drive_revisions`
    - `get_drive_revision`
- [x] Added shared drive tools to `gdrive/drive_tools.py`:
    - `list_shared_drives`
- [x] Updated `core/tool_tiers.yaml` to include these new tools in the `extended` tier for Drive.

### 2.3 Calendar
- [x] Added availability tools to `gcalendar/calendar_tools.py`:
    - `get_free_busy(time_min, time_max, items, time_zone)`
- [x] Added ACL management tools to `gcalendar/calendar_tools.py`:
    - `list_calendar_acl(calendar_id)`
    - `create_calendar_acl_rule(role, scope_type, scope_value, calendar_id)`
    - `delete_calendar_acl_rule(rule_id, calendar_id)`
- [x] Added recurrence tools to `gcalendar/calendar_tools.py`:
    - `create_recurring_event(recurrence, ...)`
- [x] Updated `auth/service_decorator.py` to support `calendar_acls` scope group mapped to `CALENDAR_SCOPE`.
- [x] Updated `core/tool_tiers.yaml` to include these new tools in the `extended` tier for Calendar.

### 2.4 Docs
- [x] Formatting wrappers
- [x] Export formats

### 2.5 Sheets
- [x] Data operations
    - `append_sheet_rows`
    - `batch_get_sheet_values`
    - `batch_update_sheet_values`
- [x] Spreadsheet structure
    - `create_named_range`, `update_named_range`, `delete_named_range`
    - `add_data_validation`
    - `set_protected_range`
- [x] Analytics
    - `create_chart`, `update_chart`
    - `create_pivot_table`

### 2.6 Slides
- [x] Opinionated builders
    - `create_slide`
    - `add_textbox`
    - `set_text_style`
    - `replace_text_everywhere`
    - `insert_image_from_url`
- [x] Export
    - `export_presentation_pdf`

### 2.7 Forms
- [x] Form building
    - `batch_update_form`
    - (Skipped `set_form_destination_sheet` due to API limitations)

### 2.8 Chat
- [x] Space management
    - `create_space`
    - `list_members`, `add_member`, `remove_member`
- [x] Threaded messaging
    - `reply_in_thread`

### 2.9 Tasks
- [x] Wrapper tools
    - `complete_task`
    - `reopen_task`
    - `set_task_due_date`

## Phase 3: Add “Workspace admin” capabilities (new apps)

### 3.1 Admin: Directory API (Admin SDK)
- [x] Create `gadmin/directory_tools.py`
- [x] Implement User management tools (`list_users`, `get_user`, `create_user`, `suspend_user`, `restore_user`)
- [x] Implement Group management tools (`list_groups`, `get_group`, `create_group`, `delete_group`, `add_group_member`, `remove_group_member`, `list_group_members`)
- [x] Update auth and configuration

### 3.2 Admin: Reports API (audit/activity)
- [x] Create `gadmin/reports_tools.py`
- [x] Implement Activity report tools (`list_admin_activities`)
- [x] Update auth and configuration

## Phase 4: Add People and Meet (new apps)

### 4.1 People (contacts)
- [x] Create `gpeople/people_tools.py`
- [x] Implement Contacts CRUD (`list_contacts`, `search_contacts`, `create_contact`, `update_contact`, `delete_contact`)
- [x] Update auth and configuration

### 4.2 Meet (meeting artefacts and records)
- [x] Create `gmeet/meet_tools.py`
- [x] Implement `list_conference_records`
- [x] Implement `get_conference_record`
- [x] Update auth and configuration

## Cross-cutting work (applies to all apps)

### Tool tiering and discoverability
- [x] Add `keep`, `admin_directory`, `admin_reports`, `people`, `meet` to `core/tool_tiers.yaml`
- [x] Verified `keep`, `admin_directory`, `admin_reports`, `people`, `meet` are in `core/tool_tiers.yaml` with appropriate core/extended tier separation.

### Auth modes
- [x] Continue supporting user OAuth for end-user flows.
- [x] Verified support for **service account + domain-wide delegation** via `GOOGLE_APPLICATION_CREDENTIALS` and `with_subject()`. This is handled by `auth/google_auth.py` and is available for admin operations and Keep.

### Consistent pagination and batching
- [x] Standardise `page_size` and `page_token` across list/search tools.
    - Drive: Updated `search_drive_files`, `list_drive_items`, `list_drive_revisions`, `list_shared_drives` to include `page_token` and consistent `page_size`.
    - Calendar: Updated `list_calendars` and `get_events` to include `page_token` and renamed `max_results` to `page_size`.
    - Admin Directory: Renamed `max_results` to `page_size` in `list_users`, `list_groups`, `list_group_members`.
    - Admin Reports: Renamed `max_results` to `page_size` in `list_admin_activities` and `list_drive_activities_via_reports`.
    - People: Renamed `limit` to `page_size` in `search_contacts`.
    - Sheets: Renamed `max_results` to `page_size` in `list_spreadsheets` and added `page_token`.
    - Verified Gmail and Meet tools already conform to the standard.
