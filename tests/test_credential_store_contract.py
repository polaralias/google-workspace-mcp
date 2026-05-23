import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class CredentialStoreContractTests(unittest.TestCase):
    def test_get_loads_repo_credentials_without_refresh_when_token_is_current(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_dir = Path(temp_dir)
            payload = {
                "oauth_client_id": "client-id",
                "oauth_client_secret": "client-secret",
                "token": "access-token",
                "refresh_token": "refresh-token",
                "expiry": "2099-01-01T00:00:00Z",
                "scopes": ["scope-a", "scope-b"],
            }
            (credentials_dir / "user@example.com.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"GOOGLE_MCP_CREDENTIALS_DIR": str(credentials_dir)}, clear=True):
                store = server.CredentialStore()
                creds = store.get("USER@example.com")

        self.assertIsNotNone(creds)
        self.assertEqual(creds.token, "access-token")
        self.assertEqual(creds.refresh_token, "refresh-token")
        self.assertEqual(set(creds.scopes or []), {"scope-a", "scope-b"})

    def test_get_returns_none_for_invalid_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_dir = Path(temp_dir)
            (credentials_dir / "user@example.com.json").write_text(
                json.dumps({"token": "missing-client-fields"}),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"GOOGLE_MCP_CREDENTIALS_DIR": str(credentials_dir)}, clear=True):
                store = server.CredentialStore()
                creds = store.get("user@example.com")

        self.assertIsNone(creds)

