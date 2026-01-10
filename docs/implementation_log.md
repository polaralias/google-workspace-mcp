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
- [ ] Opinionated builders
- [ ] Export

### 2.7 Forms
- [ ] Form building

### 2.8 Chat
- [ ] Space management
- [ ] Threaded messaging

### 2.9 Tasks
- [ ] Wrapper tools

## Phase 3: Add “Workspace admin” capabilities (new apps)

## Phase 4: Add People and Meet (new apps)
