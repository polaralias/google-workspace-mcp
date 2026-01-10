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

## Changes Implemented

### Phase 0

#### 0.1 Fix tier config gaps
- Updated `core/tool_tiers.yaml` to include missing Gmail and Sheets tools.
    - Gmail: Added `list_gmail_filters` to core tier; `create_gmail_filter`, `delete_gmail_filter` to extended tier.
    - Sheets: Added `format_sheet_range` to core tier; `add_conditional_formatting`, `update_conditional_formatting`, `delete_conditional_formatting` to extended tier.

#### 0.2 Add enablement links for new APIs
- Updated `core/api_enablement.py` with enablement links and service mappings for:
    - Google Keep (`keep.googleapis.com`)
    - Google People (`people.googleapis.com`)
    - Google Meet (`meet.googleapis.com`)
    - Google Admin SDK (`admin.googleapis.com`)

### Phase 1: Add Google Keep (new app surface)

#### 1.1 - 1.4 Implement Google Keep Tools
- Added `gkeep/keep_tools.py` with the following tools:
    - Core: `list_keep_notes`, `get_keep_note`, `create_keep_note`
    - Extended: `delete_keep_note`, `download_keep_attachment`, `share_keep_note`, `unshare_keep_note`
    - Complete: `get_keep_note_permissions`
- Updated `auth/scopes.py` with `https://www.googleapis.com/auth/keep` and `https://www.googleapis.com/auth/keep.readonly`.
- Updated `auth/service_decorator.py` to support `keep` service configuration and scopes.
- Registered `keep` tool in `main.py` (imports, icons, CLI arguments).
- Added `keep` tool tiers to `core/tool_tiers.yaml`.

### Phase 2: Expand existing apps (deepen function coverage)

#### 2.1 Gmail
- Added message lifecycle helpers to `gmail/gmail_tools.py`:
    - `archive_gmail_message`
    - `trash_gmail_message`
    - `mark_gmail_read_unread`
    - `star_unstar_gmail_message`
- Updated `core/tool_tiers.yaml` to include these new tools in the `extended` tier for Gmail.
