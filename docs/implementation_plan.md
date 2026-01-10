## Phase 0: Repo alignment fixes (quick wins)

### 0.1 Fix tier config gaps (tools implemented but not reachable in tier mode)

Update `core/tool_tiers.yaml` so these existing tools are included under an appropriate tier:

* Gmail

  * `list_gmail_filters`, `create_gmail_filter`, `delete_gmail_filter`
* Sheets

  * `format_sheet_range`
  * `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting`

Deliverables

* Updated `core/tool_tiers.yaml`
* README tool inventory refreshed so it matches what is actually registered.

### 0.2 Add enablement links for new APIs you’ll introduce

Extend `core/api_enablement.py` with API IDs and enablement links for:

* `keep.googleapis.com` (Google Keep API) ([Google for Developers][1])
* `people.googleapis.com` (People API) ([Google for Developers][2])
* `meet.googleapis.com` (Google Meet API) ([Google for Developers][3])
* `admin.googleapis.com` (Admin SDK: Directory + Reports) ([Google for Developers][4])

---

## Phase 1: Add Google Keep (new app surface)

### 1.1 APIs to use

* **Google Keep API** (`keep.googleapis.com`, v1) ([Google for Developers][1])

  * Notes: create, list, get, delete ([Google for Developers][1])
  * Attachments: download via `media.download` (requires `alt=media`, and `mimeType` when downloading media) ([Google for Developers][5])
  * Sharing: `notes.permissions.batchCreate` and `notes.permissions.batchDelete` (writer permissions management) ([Google for Developers][6])

### 1.2 Scopes

Add to `auth/scopes.py`:

* `https://www.googleapis.com/auth/keep`
* `https://www.googleapis.com/auth/keep.readonly` (optional, if you want read-only mode) ([Google for Developers][7])

Also document (and optionally implement) **domain-wide delegation** as an auth option, since Google’s Keep guidance explicitly calls it out. ([Google for Developers][8])

### 1.3 MCP tool set to implement (Keep)

Create a new module `gkeep/keep_tools.py`, and register a `keep` service in `main.py` (`--tools` choices, imports, icon).

Core (recommended)

* `list_keep_notes(filter: str | None, page_size: int, page_token: str | None)`

  * API: `notes.list` with `filter` supporting `createTime`, `updateTime`, `trashTime`, `trashed` ([Google for Developers][7])
* `get_keep_note(note_name: str)`

  * API: `notes.get` ([Google for Developers][9])
* `create_keep_note(title: str, text: str | None, list_items: [{text, checked}] | None)`

  * API: `notes.create` (Note body is a Section with `text` or `list`) ([Google for Developers][10])

Extended

* `delete_keep_note(note_name: str)`

  * API: `notes.delete` ([Google for Developers][1])
* `download_keep_attachment(attachment_name: str, mime_type: str)`

  * API: `media.download` ([Google for Developers][5])
* `share_keep_note(note_name: str, writers: [email|groupEmail])`

  * API: `notes.permissions.batchCreate` (writer role creation) ([Google for Developers][11])
* `unshare_keep_note(note_name: str, emails_or_groups: [...])`

  * API: `notes.permissions.batchDelete` ([Google for Developers][6])

Complete (optional)

* `get_keep_note_permissions(note_name: str)`

  * Implementation: call `notes.get` and return the `permissions` field (output-only) ([Google for Developers][12])

### 1.4 Important limitation to document plainly

Because the REST surface does not include an update/patch method, your Keep integration should be positioned as:

* **Create** notes and **retrieve** notes
* **Delete** notes
* **Download** attachments
* **Manage** sharing permissions
  Not “full Keep parity”, since labels, reminders, pin/colour/archive and editing existing note content are not part of the official REST reference. ([Google for Developers][1])

---

## Phase 2: Expand existing apps (deepen function coverage)

Below is split by app, including which API to use and the concrete functions to add.

### Gmail (Gmail API v1)

API

* Gmail API (`gmail.googleapis.com`, v1)

Add tools

* Message lifecycle helpers (clearer than label juggling)

  * `archive_gmail_message`, `trash_gmail_message`, `mark_gmail_read_unread`, `star_unstar_gmail_message`
  * API: `users.messages.modify` with system labels (INBOX, TRASH, UNREAD, STARRED)
* Settings beyond filters (optional but high value)

  * signature, vacation responder, forwarding
  * API: Gmail settings endpoints (typically under `users.settings.*`)

Also fix tier exposure for existing filter tools (Phase 0).

### Drive (Drive API v3, plus Revisions)

API

* Drive API v3 (`drive.googleapis.com`, v3)
* Revisions endpoints (`revisions.list`, `revisions.get`) ([Google for Developers][13])

Add tools

* File lifecycle

  * `create_drive_folder` (Drive files.create with folder mimeType)
  * `copy_drive_file` (files.copy)
  * `trash_drive_file`, `untrash_drive_file`, `delete_drive_file` (files.update / files.delete)
* Revisions and recovery

  * `list_drive_revisions` (revisions.list) ([Google for Developers][14])
  * `get_drive_revision` (revisions.get) ([Google for Developers][13])
* Shared drives parity

  * `list_shared_drives` (drives.list)
  * `list_shared_drive_items` (files.list with `driveId`, `corpora=drive`)

### Calendar (Calendar API v3)

API

* Google Calendar API (`calendar-json.googleapis.com`, v3)

Add tools

* Availability

  * `get_free_busy(time_min, time_max, calendars[])` (freebusy.query)
  * `suggest_meeting_times(attendees, duration, constraints)` (can be built on freebusy + heuristics)
* Sharing/ACL

  * `list_calendar_acl`, `create_calendar_acl_rule`, `delete_calendar_acl_rule`
* Recurrence ergonomics

  * `create_recurring_event(rrule, exceptions)` (wrapper that produces correct event resource)

### Docs (Docs API v1)

API

* Google Docs API (`docs.googleapis.com`, v1)

Add tools

* Formatting wrappers (opinionated helpers that emit batchUpdate)

  * `apply_doc_paragraph_style` (heading levels)
  * `apply_doc_text_style` (bold/italic/links)
* Export formats

  * `export_doc(format: pdf|docx|html)` (Drive files.export for Docs)

### Sheets (Sheets API v4)

API

* Google Sheets API (`sheets.googleapis.com`, v4)

You already have conditional formatting and range formatting implemented; expose them via tiers (Phase 0).

Add tools

* Data operations

  * `append_sheet_rows` (spreadsheets.values.append)
  * `batch_get_sheet_values`, `batch_update_sheet_values` (values.batchGet / values.batchUpdate)
* Spreadsheet structure

  * `create_named_range`, `update_named_range`, `delete_named_range`
  * `add_data_validation`, `set_protected_range`
* Analytics

  * `create_chart`, `update_chart`
  * `create_pivot_table`

### Slides (Slides API v1)

API

* Google Slides API (`slides.googleapis.com`, v1)

Add tools

* Opinionated builders (reduce reliance on raw batchUpdate)

  * `create_slide(layout)`, `add_textbox`, `set_text_style`
  * `replace_text_everywhere`
  * `insert_image_from_url_or_drive`
* Export

  * `export_presentation_pdf` (Drive files.export for Slides)

### Forms (Forms API v1)

API

* Google Forms API (`forms.googleapis.com`, v1)

Add tools

* Form building

  * `batch_update_form` for adding/updating questions (Forms batchUpdate equivalent)
  * `set_form_destination_sheet(spreadsheetId)` (responses destination)

### Chat (Google Chat API)

API

* Google Chat API (`chat.googleapis.com`, v1)

Add tools

* Space management

  * `create_space`
  * `list_members`, `add_member`, `remove_member`
* Threaded messaging

  * `reply_in_thread(thread_id, message)`

### Tasks (Tasks API v1)

API

* Google Tasks API (`tasks.googleapis.com`, v1)

Add tools

* Minor but useful wrappers

  * `complete_task`, `reopen_task` (status updates)
  * `set_task_due_date` (normalise date handling)

---

## Phase 3: Add “Workspace admin” capabilities (new apps)

### 3.1 Admin: Directory API (Admin SDK)

API

* **Admin SDK Directory API** (Admin SDK) ([Google for Developers][4])

Add tools (suggested baseline)

* Users

  * `list_users`, `get_user`, `create_user`, `suspend_user`, `restore_user`
* Groups

  * `list_groups`, `get_group`, `create_group`, `delete_group`
  * `add_group_member`, `remove_group_member`, `list_group_members`

Scopes

* Add the minimum required Directory scopes (start with read-only variants, add write variants in higher tiers).

### 3.2 Admin: Reports API (audit/activity)

API

* **Admin SDK Reports API** (activities and usage reports) ([Google for Developers][15])

Add tools

* `list_admin_activities(application, userKey|all, startTime, endTime, filters)`

  * API: `activities.list` ([Google for Developers][16])
* `list_drive_activities_via_reports(...)` (if you want Drive activity without Drive Activity API)

This becomes the backbone for “what changed?” and security workflows.

---

## Phase 4: Add People and Meet (new apps)

### 4.1 People (contacts)

API

* **People API** (`people.googleapis.com`) ([Google for Developers][2])

Add tools

* Contacts CRUD

  * `list_contacts`, `search_contacts`
  * `create_contact`, `update_contact`, `delete_contact`
* “Other contacts” and directory lookups (optional, depending on your needs)

### 4.2 Meet (meeting artefacts and records)

API

* **Google Meet API v2** (`meet.googleapis.com`, v2) ([Google for Developers][3])

Add tools

* `list_conference_records` (conferenceRecords.list) ([Google for Developers][17])
* `get_conference_record`
* Follow-on artefacts (participants, recordings, transcripts) depending on what your users need most

---

## Cross-cutting work (applies to all apps)

### Tool tiering and discoverability

* Add `keep`, `admin_directory`, `admin_reports`, `people`, `meet` to `core/tool_tiers.yaml`.
* Keep “core” tiers safe and mostly read-only where possible; push write and admin-heavy operations to extended/complete.

### Auth modes

* Continue supporting user OAuth for end-user flows.
* Add an optional **service account + domain-wide delegation** mode for admin-grade operations and Keep (Google’s Keep docs explicitly mention domain-wide delegation as an auth option). ([Google for Developers][8])

### Consistent pagination and batching

* Standardise `page_size` and `page_token` across list/search tools, including Keep’s `nextPageToken` model. ([Google for Developers][7])

[1]: https://developers.google.com/workspace/keep/api/reference/rest "Google Keep API  |  Google for Developers"
[2]: https://developers.google.com/people?utm_source=chatgpt.com "Introduction | People API"
[3]: https://developers.google.com/workspace/meet/api/reference/rest/v2?utm_source=chatgpt.com "Google Meet API"
[4]: https://developers.google.com/workspace/admin/directory/v1/guides?utm_source=chatgpt.com "Directory API Overview | Admin console"
[5]: https://developers.google.com/workspace/keep/api/reference/rest/v1/media/download?utm_source=chatgpt.com "Method: media.download | Google Keep"
[6]: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes.permissions?utm_source=chatgpt.com "REST Resource: notes.permissions | Google Keep"
[7]: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes/list "Method: notes.list  |  Google Keep  |  Google for Developers"
[8]: https://developers.google.com/workspace/keep/api/guides?utm_source=chatgpt.com "Google Keep API Overview"
[9]: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes/get "Method: notes.get  |  Google Keep  |  Google for Developers"
[10]: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes/create "Method: notes.create  |  Google Keep  |  Google for Developers"
[11]: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes.permissions/batchCreate?utm_source=chatgpt.com "Method: notes.permissions.batchCreate | Google Keep"
[12]: https://developers.google.com/workspace/keep/api/reference/rest/v1/notes "REST Resource: notes  |  Google Keep  |  Google for Developers"
[13]: https://developers.google.com/workspace/drive/api/reference/rest/v3/revisions/get?utm_source=chatgpt.com "Method: revisions.get | Google Drive"
[14]: https://developers.google.com/workspace/drive/api/reference/rest/v2/revisions/list?utm_source=chatgpt.com "Method: revisions.list | Google Drive"
[15]: https://developers.google.com/workspace/admin/reports/v1/get-start/overview?utm_source=chatgpt.com "Reports API Overview | Admin console"
[16]: https://developers.google.com/workspace/admin/reports/reference/rest/v1/activities/list?utm_source=chatgpt.com "Method: activities.list | Admin console"
[17]: https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords/list?utm_source=chatgpt.com "Method: conferenceRecords.list | Google Meet"
