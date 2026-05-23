import unittest
from unittest.mock import patch
from pathlib import Path

from fastmcp.tools import FunctionTool

import server


class _EmptyStore:
    def get(self, _email):
        return None


class _FakeKeepBackend:
    def __init__(self, configured=False):
        self.configured = configured
        self.managed_label_name = "google-workspace-mcp"
        self.unsafe_mode = False


class _FakeCredentialStore:
    base_dir = Path("C:/tmp/google-workspace-mcp-tests")


class _FakeServer:
    def __init__(self):
        self.tools = []

    def add_tool(self, tool: FunctionTool):
        self.tools.append(tool)


class AuthContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_static_api_key_verifier_accepts_known_token_and_rejects_unknown_token(self):
        verifier = server.StaticApiKeyVerifier(["alpha", "beta"])

        accepted = await verifier.verify_token("beta")
        rejected = await verifier.verify_token("gamma")

        self.assertIsNotNone(accepted)
        self.assertEqual(accepted.client_id, "google-workspace-mcp")
        self.assertEqual(accepted.scopes, [])
        self.assertIsNone(rejected)

    async def test_svc_permission_error_does_not_reference_service_accounts(self):
        with patch.dict("os.environ", {}, clear=True):
            runtime = server.GoogleRuntime(_EmptyStore())

            with self.assertRaises(PermissionError) as exc:
                runtime._svc("user@example.com", "drive", "v3")

        message = str(exc.exception)
        self.assertIn("OAuth credential", message)
        self.assertIn("GOOGLE_API_KEY", message)
        self.assertNotIn("GOOGLE_SERVICE_ACCOUNT_FILE", message)
        self.assertNotIn("GOOGLE_SERVICE_ACCOUNT_JSON", message)

    async def test_health_payload_only_reports_supported_auth_fields(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "public-key"}, clear=True):
            payload = server._health_payload(_FakeCredentialStore(), _FakeKeepBackend(configured=False))

        self.assertEqual(payload["googleAuthSources"], ["google_api_key", "oauth_credentials_dir"])
        self.assertNotIn("serviceAccountConfigured", payload)
        self.assertNotIn("defaultImpersonatedUser", payload)

    async def test_registered_tool_schema_does_not_claim_service_account_or_impersonation_support(self):
        fake_server = _FakeServer()
        runtime = server.GoogleRuntime(_EmptyStore())
        manifest = [
            {
                "name": "public_tool",
                "description": "desc",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_google_email": {
                            "type": "string",
                            "description": "The user's Google email address.",
                        }
                    },
                    "required": ["user_google_email"],
                },
            }
        ]

        server._register_tools(fake_server, runtime, manifest)

        tool = fake_server.tools[0]
        description = tool.parameters["properties"]["user_google_email"]["description"]
        self.assertNotIn("service-account", description)
        self.assertNotIn("GOOGLE_IMPERSONATED_USER", description)
