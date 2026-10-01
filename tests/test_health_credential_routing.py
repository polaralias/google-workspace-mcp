import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import health_dispatch
import server

EMAIL = 'owner@example.com'
HEALTH_SCOPE = 'https://www.googleapis.com/auth/googlehealth.profile.readonly'


class HealthCredentialRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_and_workspace_use_distinct_grants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace, health = root / 'workspace', root / 'health'
            for folder, token, scopes in [(workspace, 'workspace-token', ['calendar']),
                                          (health, 'health-token', [HEALTH_SCOPE])]:
                folder.mkdir()
                (folder / (EMAIL + '.json')).write_text(json.dumps({
                    'oauth_client_id': 'client', 'oauth_client_secret': 'secret',
                    'token': token, 'scopes': scopes, 'expiry': '2099-01-01T00:00:00Z',
                }))
            with patch.dict('os.environ', {'GOOGLE_MCP_CREDENTIALS_DIR': str(workspace),
                                          'GOOGLE_HEALTH_CREDENTIALS_DIR': str(health),
                                          'GOOGLE_DEFAULT_USER_EMAIL': EMAIL}):
                runtime = server.GoogleRuntime(server.CredentialStore())
                with patch.object(health_dispatch, '_request', return_value={}) as request:
                    await runtime.dispatch('health_get_profile', {})
                    self.assertEqual(request.call_args.args[0].token, 'health-token')
                with patch.object(server, 'build') as build:
                    runtime._svc(EMAIL, 'calendar', 'v3')
                    self.assertEqual(build.call_args.kwargs['credentials'].token, 'workspace-token')

    async def test_missing_dedicated_grant_fails_without_workspace_fallback(self):
        class WorkspaceStore:
            def get(self, email):
                raise AssertionError('Health must not read the Workspace store')
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict('os.environ', {'GOOGLE_HEALTH_CREDENTIALS_DIR': directory,
                                          'GOOGLE_DEFAULT_USER_EMAIL': EMAIL}):
                runtime = server.GoogleRuntime(WorkspaceStore())
                with patch.object(health_dispatch, '_request') as request:
                    with self.assertRaisesRegex(PermissionError, 'credentials are missing'):
                        await runtime.dispatch('health_get_profile', {})
                    request.assert_not_called()

    async def test_unconfigured_health_directory_preserves_existing_store(self):
        store = object()
        with patch.dict('os.environ', {'GOOGLE_HEALTH_CREDENTIALS_DIR': ''}):
            runtime = server.GoogleRuntime(store)
            with patch.object(server, '_dispatch_health_impl', return_value={}) as dispatch:
                await runtime.dispatch('health_get_profile', {})
                self.assertIs(dispatch.call_args.args[0], store)
