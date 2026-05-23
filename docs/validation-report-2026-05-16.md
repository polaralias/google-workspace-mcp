# Validation Report - 2026-05-16

Historical artifact note:

- This report captures the live validation state from 2026-05-16.
- Some issues described here have since been repaired, narrowed, or removed from the supported product contract.
- Use [product-specs/support-matrix.md](docs\product-specs\support-matrix.md) for current verified support.

## Scope

This report covers live validation performed against real Google services on 2026-05-16 using:

- repo-local OAuth credential for `user@example.com`
- Google Keep master-token auth
- the repository's `uv`-managed Python environment

Validation policy used:

- perform read actions before write actions
- only perform harmful write actions on artifacts created during validation

## Environment findings

- Running `python server.py` directly in the host interpreter failed at first because `gkeepapi` was not installed there.
- Running through `uv run` succeeded and created a usable `.venv/`.
- The repo's practical runtime path is therefore `uv run ...` or the helper scripts that depend on that environment.

## Auth findings

### Verified working

- Stored OAuth credential loading from `.oauth/`
- Google Keep master-token auth
- MCP health surface

### Verified not sufficient by itself

- `GOOGLE_API_KEY` alone does not unlock most Workspace APIs used by this project.

Observed examples:

- Calendar rejected API-key-only auth
- Gmail rejected API-key-only auth
- Tasks rejected API-key-only auth
- People rejected API-key-only auth
- Drive API-key-only path returned an expired-key error with the provided key

### API-key-only validation with fresh key

A second pass was run with:

- fresh `GOOGLE_API_KEY`
- OAuth loading intentionally disabled
- Keep auth intentionally disabled

This established the actual public-read boundary of the current implementation.

#### Verified working in API-key-only mode

- `get_spreadsheet_info` on a public spreadsheet
- `read_sheet_values` on a public spreadsheet
- `export_presentation_pdf` on a public presentation via Drive export
- `get_drive_file_permissions` on a public Drive file

#### Verified failing in API-key-only mode

- `list_calendars`
- `search_gmail_messages`
- `list_task_lists`
- `list_contacts`
- `get_doc_content` on a public Google Doc
- `get_presentation` on a public Slides presentation
- `search_drive_files` did not function as a useful public-search path in this validation

#### Verified incorrect behavior in API-key-only mode

- `get_drive_file_content` on a public plain text file returned file metadata rendered as a string instead of the actual file content bytes

This means the API-key-only mode is real but narrow:

- some public Drive/Sheets export and read flows work
- many user-scoped APIs still require OAuth
- some higher-level wrappers are incorrect even when API-key auth is accepted

## Health and startup

Verified:

- server import succeeds in the `uv` environment
- server health payload reports configured auth sources correctly
- HTTP health endpoint responds when the server is started under the managed environment

## Live domain validation

### Passed end-to-end

#### Google Keep

Verified:

- list notes
- list labels
- create note
- read created note
- update created note
- delete created note

Notes:

- deletion succeeded in practice
- returned delete payload looked stale, but follow-up read confirmed the note was gone

#### Calendar

Verified:

- list calendars
- create event
- read created event by ID
- delete created event

#### Tasks

Verified:

- list task lists
- create task list
- list tasks in created list
- create task
- list tasks again
- update created task
- delete created task
- delete created task list

#### Drive folder lifecycle

Verified:

- list drive root items
- create folder
- list created folder contents
- delete created folder

#### Docs

Verified:

- create document
- read document content
- modify document text
- read modified content
- delete created document via Drive delete

Note:

- the live wrapper returns document text in the `text` field, not `content`

#### Slides

Verified:

- create presentation
- read presentation
- create slide
- read presentation again
- delete created presentation via Drive delete

#### Contacts

Verified:

- list contacts
- create contact
- update created contact
- delete created contact

### Passed read-only

#### Gmail

Verified:

- search messages

#### Drive search

Verified:

- search drive files

#### Contacts search

Partially verified:

- `search_contacts` executed successfully
- it did not immediately return the contact created earlier in the same validation flow

This may be eventual consistency or search behavior rather than a hard failure, but it should not be treated as proven for immediate read-after-write use.

## Concrete bugs and defects found

### 1. `create_drive_file` is broken

Observed behavior:

- calling `create_drive_file` with string `content` raised `googleapiclient.errors.UnknownFileType`

Cause in current implementation:

- the code passes `media_body=args["content"]` directly into the Drive client
- the client interprets that string as a filename/media descriptor rather than file contents

Impact:

- the declared plain text file creation path is not actually working

### 1a. `get_drive_file_content` is incorrect for API-key public file reads

Observed behavior:

- when pointed at a public plain text file in API-key-only mode, the wrapper returned a stringified metadata object rather than the file contents

Impact:

- the endpoint cannot currently be trusted as a generic public file content reader
- at least one supported-looking API-key read path is semantically wrong

### 2. Keep delete response is misleading

Observed behavior:

- `delete_keep_note` returned `updated: true`
- returned note payload still appeared untrashed/unmodified
- follow-up read showed the note was no longer available

Impact:

- actual delete behavior may work, but callers should not trust the returned note state

### 3. Runtime portability depends on managed environment

Observed behavior:

- direct host interpreter execution failed on missing dependency
- `uv run` worked

Impact:

- local run instructions are only reliable when they go through the project-managed environment

## Operational conclusions

### Verified strong surfaces

- OAuth credential loading
- Keep master-token backend
- Calendar event lifecycle
- Tasks lifecycle
- Drive folder lifecycle
- Docs basic lifecycle
- Slides basic lifecycle
- Contacts create/update/delete

### Verified weak or partial surfaces

- Drive file creation wrapper
- Keep delete return payload fidelity
- Contacts search immediate read-after-write behavior
- API-key-only fallback path for most Workspace surfaces

## Recommended next validation passes

1. Add a structured test matrix for all declared tools, with status:
   - untested
   - read-only verified
   - write-path verified
   - known broken

2. Validate remaining declared surfaces not exercised here:
   - Sheets operations
   - Forms batch update
   - Meet conference records
   - Chat tools
   - Admin/calendar ACL tools
   - Gmail mutation tools

3. Fix `create_drive_file` before claiming Drive file create/write support publicly.

4. Add regression tests around the live wrapper behavior that was proven here, especially:
   - credential loading
   - Calendar create/get/delete
   - Tasks lifecycle
   - Docs create/read/update/delete
   - Slides create/read/add slide/delete
   - Drive folder create/list/delete
