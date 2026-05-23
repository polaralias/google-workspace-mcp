import unittest

import server


class _FakeStore:
    def get(self, _email):
        return None


class _FakeKeep:
    def __init__(self):
        self.synced = False

    def sync(self):
        self.synced = True


class _FakeNote:
    def __init__(self, note_id):
        self.id = note_id
        self.deleted = False

    def delete(self):
        self.deleted = True


class _FakeKeepBackend:
    configured = True

    def __init__(self):
        self.keep = _FakeKeep()
        self.note = _FakeNote("note-123")

    def get_note_or_raise(self, user_email, note_name):
        self.last_user_email = user_email
        self.last_note_name = note_name
        return self.keep, self.note

    def ensure_modifiable(self, note):
        self.last_checked_note = note

    def serialize_note(self, note):
        return {"id": note.id, "trashed": False}


class KeepContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_delete_keep_note_returns_authoritative_delete_result(self):
        runtime = server.GoogleRuntime(_FakeStore())
        backend = _FakeKeepBackend()
        runtime._keep_master_token = backend

        result = await runtime.dispatch(
            "delete_keep_note",
            {
                "user_google_email": "user@example.com",
                "note_name": "notes/note-123",
            },
        )

        self.assertEqual(result, {"deleted": True, "noteName": "notes/note-123"})
        self.assertTrue(backend.keep.synced)
        self.assertTrue(backend.note.deleted)
