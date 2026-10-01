---
type: "Product Contract"
title: "Google Health API surface"
description: "Defines the Google Health API MCP contract and its evidence boundary."
authority: canonical
verification: untested
owner: polaralias
---

# Google Health API surface

The server exposes Google Health API v4 separately from Google Workspace. Google Health calls use stored Google OAuth credentials for the selected account. API keys and Keep master tokens never authorize Health calls. Health scopes are requested only through explicit Health profiles, separate from the existing Workspace profiles.

Set `GOOGLE_HEALTH_CREDENTIALS_DIR` to route only Health tools to a separate credential directory. Workspace tools retain `GOOGLE_MCP_CREDENTIALS_DIR`. If the Health directory is unset, the existing shared-store behavior remains; if it is set but the account's Health grant is missing, Health calls fail without falling back to Workspace credentials.

The consent helper saves Health profiles to `GOOGLE_HEALTH_CREDENTIALS_DIR` or `.oauth-health`, and updates only that directory setting. It excludes previously granted scopes to avoid combining Workspace scopes with a Health grant. Use `--credentials-dir` to specify an explicit host destination.

The checked-in Health catalog is an allowlist of Google's documented data types, operations, and read/write scopes. A generic data-point tool may only call an operation listed for its selected data type. Resource names must stay under `users/me/dataTypes/{selected-type}`. The server rejects unsupported operations, data types, malformed names, missing credentials, and missing OAuth scopes before calling Google.

Public operations cover list, get, create, patch, batch delete, reconcile, rollup, and daily rollup where Google's data-type matrix permits them. Exercise TCX export and user profile/settings endpoints use dedicated tools. Inputs and responses use Google's v4 JSON shapes. The server does not infer nutrition intake from calorie expenditure: nutrition logs record calories consumed; active energy and exercise summaries record calories burned. A workout summary alone does not populate raw daily activity totals.

Only bounded page sizes and explicit pagination tokens are accepted. Writes send only the selected data point's body; arbitrary URLs, path traversal, cross-account resource names, and caller-supplied bearer tokens are rejected. The server does not automatically replay a write after an uncertain transport failure.

Acceptance requires offline tests for every catalog row and operation gate, OAuth scope separation, request construction, pagination, write constraints, and representative workout and nutrition payloads. Live support is claimed only after a consented Google Health project successfully reads and writes disposable data, with cleanup verified. Google's current notice says new projects are not being onboarded, so contract tests and live verification are reported separately.
