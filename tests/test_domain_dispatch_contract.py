import unittest
from unittest.mock import patch

import server


class _FakeStore:
    def get(self, _email):
        return object()


class _FakeExecute:
    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class _CalendarFreeBusyService:
    def __init__(self):
        self.body = None

    def freebusy(self):
        return self

    def query(self, body):
        self.body = body
        return _FakeExecute({"calendars": {}})


class _DocsDocumentsService:
    def __init__(self):
        self.batch_update_calls = []

    def create(self, body):
        return _FakeExecute({"documentId": "doc-123", "title": body["title"]})

    def batchUpdate(self, documentId, body):
        self.batch_update_calls.append((documentId, body))
        return _FakeExecute({"documentId": documentId})


class _DocsService:
    def __init__(self):
        self._documents = _DocsDocumentsService()

    def documents(self):
        return self._documents


class _GmailMessagesService:
    def get(self, **kwargs):
        if kwargs["id"] == "bad":
            raise RuntimeError("boom")
        return _FakeExecute({"id": kwargs["id"], "payload": {"headers": []}})


class _GmailSettingsFiltersService:
    def create(self, **kwargs):
        return _FakeExecute({"id": "filter-123", **kwargs["body"]})


class _GmailUsersService:
    def messages(self):
        return _GmailMessagesService()

    def settings(self):
        return self

    def filters(self):
        return _GmailSettingsFiltersService()


class _GmailService:
    def users(self):
        return _GmailUsersService()


class _SheetsValuesService:
    def __init__(self):
        self.update_kwargs = None

    def update(self, **kwargs):
        self.update_kwargs = kwargs
        return _FakeExecute({"updatedRows": 1})


class _SheetsSpreadsheetsService:
    def __init__(self):
        self._values = _SheetsValuesService()

    def values(self):
        return self._values


class _SheetsService:
    def __init__(self):
        self._spreadsheets = _SheetsSpreadsheetsService()

    def spreadsheets(self):
        return self._spreadsheets


class _SlidesPresentationsService:
    def batchUpdate(self, **kwargs):
        return _FakeExecute(kwargs)


class _SlidesService:
    def presentations(self):
        return _SlidesPresentationsService()


class _TasksTasksService:
    def __init__(self):
        self.patch_kwargs = None

    def patch(self, **kwargs):
        self.patch_kwargs = kwargs
        return _FakeExecute({"id": kwargs["task"], **kwargs["body"]})


class _TasksService:
    def __init__(self):
        self._tasks = _TasksTasksService()

    def tasks(self):
        return self._tasks


class _PeoplePeopleService:
    def __init__(self):
        self.updated_body = None
        self.search_calls = []

    def get(self, **kwargs):
        return _FakeExecute({"etag": "etag-123"})

    def updateContact(self, **kwargs):
        self.updated_body = kwargs["body"]
        return _FakeExecute({"resourceName": kwargs["resourceName"], "etag": kwargs["body"]["etag"]})

    def searchContacts(self, **kwargs):
        self.search_calls.append(kwargs)
        if kwargs["query"] == "":
            return _FakeExecute({"results": []})
        return _FakeExecute({"results": [{"person": {"resourceName": "people/c123"}}]})


class _PeopleService:
    def __init__(self):
        self._people = _PeoplePeopleService()

    def people(self):
        return self._people


class _FormsFormsService:
    def batchUpdate(self, **kwargs):
        return _FakeExecute(kwargs["body"])


class _FormsService:
    def forms(self):
        return _FormsFormsService()


class _MeetConferenceRecordsService:
    def list(self, **kwargs):
        return _FakeExecute({"conferenceRecords": [{"name": "records/1"}]})


class _MeetService:
    def conferenceRecords(self):
        return _MeetConferenceRecordsService()


class DomainDispatchContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_calendar_free_busy_accepts_string_items_payload(self):
        runtime = server.GoogleRuntime(_FakeStore())
        svc = _CalendarFreeBusyService()

        with patch.object(runtime, "_svc", return_value=svc):
            result = await runtime.dispatch(
                "get_free_busy",
                {
                    "user_google_email": "user@example.com",
                    "items": '[{"id":"primary"}]',
                    "time_min": "2026-05-19T10:00:00Z",
                    "time_max": "2026-05-19T11:00:00Z",
                },
            )

        self.assertEqual(result, {"freeBusy": {"calendars": {}}})
        self.assertEqual(svc.body["items"], [{"id": "primary"}])

    async def test_create_doc_inserts_initial_content_after_creation(self):
        runtime = server.GoogleRuntime(_FakeStore())
        svc = _DocsService()

        with patch.object(runtime, "_svc", return_value=svc):
            result = await runtime.dispatch(
                "create_doc",
                {"user_google_email": "user@example.com", "title": "Doc", "content": "hello"},
            )

        self.assertTrue(result["created"])
        self.assertEqual(
            svc.documents().batch_update_calls,
            [("doc-123", {"requests": [{"insertText": {"location": {"index": 1}, "text": "hello"}}]})],
        )

    async def test_gmail_batch_content_reports_per_message_errors_without_aborting_batch(self):
        runtime = server.GoogleRuntime(_FakeStore())

        with patch.object(runtime, "_svc", return_value=_GmailService()):
            result = await runtime.dispatch(
                "get_gmail_messages_content_batch",
                {
                    "user_google_email": "user@example.com",
                    "message_ids": ["good", "bad"],
                    "format": "metadata",
                },
            )

        self.assertEqual(result["results"][0]["messageId"], "good")
        self.assertEqual(result["results"][1], {"messageId": "bad", "error": "boom"})

    async def test_modify_sheet_values_parses_json_string_payload(self):
        runtime = server.GoogleRuntime(_FakeStore())
        svc = _SheetsService()

        with patch.object(runtime, "_svc", return_value=svc):
            result = await runtime.dispatch(
                "modify_sheet_values",
                {
                    "user_google_email": "user@example.com",
                    "spreadsheet_id": "sheet-123",
                    "range_name": "A1:B1",
                    "values": '[["a","b"]]',
                },
            )

        self.assertTrue(result["updated"])
        self.assertEqual(svc.spreadsheets().values().update_kwargs["body"], {"values": [["a", "b"]]})

    async def test_set_text_style_requires_at_least_one_style_field(self):
        runtime = server.GoogleRuntime(_FakeStore())

        with patch.object(runtime, "_svc", return_value=_SlidesService()):
            with self.assertRaises(ValueError) as exc:
                await runtime.dispatch(
                    "set_text_style",
                    {
                        "user_google_email": "user@example.com",
                        "presentation_id": "pres-123",
                        "object_id": "shape-1",
                    },
                )

        self.assertIn("At least one style field is required", str(exc.exception))

    async def test_set_task_due_date_normalizes_due_timestamp(self):
        runtime = server.GoogleRuntime(_FakeStore())
        svc = _TasksService()

        with patch.object(runtime, "_svc", return_value=svc):
            result = await runtime.dispatch(
                "set_task_due_date",
                {
                    "user_google_email": "user@example.com",
                    "task_list_id": "list-123",
                    "task_id": "task-123",
                    "due": "2026-05-19",
                },
            )

        self.assertTrue(result["updated"])
        self.assertEqual(
            svc.tasks().patch_kwargs["body"]["due"],
            "2026-05-19T00:00:00.000Z",
        )

    async def test_update_contact_backfills_etag_when_missing(self):
        runtime = server.GoogleRuntime(_FakeStore())
        svc = _PeopleService()

        with patch.object(runtime, "_svc", return_value=svc):
            result = await runtime.dispatch(
                "update_contact",
                {
                    "user_google_email": "user@example.com",
                    "resource_name": "people/c123",
                    "person": {"names": [{"givenName": "A"}]},
                    "update_person_fields": "names",
                },
            )

        self.assertTrue(result["updated"])
        self.assertEqual(svc.people().updated_body["etag"], "etag-123")

    async def test_search_contacts_warms_people_cache_before_real_query(self):
        runtime = server.GoogleRuntime(_FakeStore())
        svc = _PeopleService()

        with patch.object(runtime, "_svc", return_value=svc):
            result = await runtime.dispatch(
                "search_contacts",
                {
                    "user_google_email": "user@example.com",
                    "query": "alex",
                    "page_size": 5,
                },
            )

        self.assertEqual(result["results"][0]["person"]["resourceName"], "people/c123")
        self.assertEqual(
            svc.people().search_calls,
            [
                {
                    "query": "",
                    "pageSize": 1,
                    "readMask": "names,emailAddresses,phoneNumbers,organizations,metadata",
                },
                {
                    "query": "alex",
                    "pageSize": 5,
                    "readMask": "names,emailAddresses,phoneNumbers,organizations,metadata",
                },
            ],
        )

    async def test_batch_update_form_requires_list_requests(self):
        runtime = server.GoogleRuntime(_FakeStore())

        with patch.object(runtime, "_svc", return_value=_FormsService()):
            with self.assertRaises(ValueError) as exc:
                await runtime.dispatch(
                    "batch_update_form",
                    {
                        "user_google_email": "user@example.com",
                        "form_id": "form-123",
                        "requests": {"not": "a list"},
                    },
                )

        self.assertIn("requests must be a list", str(exc.exception))

    async def test_list_conference_records_returns_records_payload(self):
        runtime = server.GoogleRuntime(_FakeStore())

        with patch.object(runtime, "_svc", return_value=_MeetService()):
            result = await runtime.dispatch(
                "list_conference_records",
                {"user_google_email": "user@example.com"},
            )

        self.assertEqual(result["conferenceRecords"], [{"name": "records/1"}])
