import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import google_oauth_helper as helper


class HealthConsentRoutingTests(unittest.TestCase):
    def test_health_default_does_not_use_workspace_directory(self):
        with patch.dict(os.environ, {'GOOGLE_MCP_CREDENTIALS_DIR': '/workspace'}, clear=True):
            self.assertEqual(helper._credential_store_dir(health=True), helper.REPO_ROOT / '.oauth-health')
            self.assertEqual(helper._credential_store_dir(), Path('/workspace'))

    def test_configured_health_directory_is_used(self):
        with patch.dict(os.environ, {'GOOGLE_HEALTH_CREDENTIALS_DIR': 'health-grants'}, clear=True):
            self.assertEqual(helper._credential_store_dir(health=True), helper.REPO_ROOT / 'health-grants')

    def test_consent_profiles_keep_scope_and_directory_updates_separate(self):
        for profile, variable, include_granted in [
            ('health', 'GOOGLE_HEALTH_CREDENTIALS_DIR', 'false'),
            ('workspace', 'GOOGLE_MCP_CREDENTIALS_DIR', 'true'),
        ]:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                flow = Mock()
                with patch.object(helper, 'load_env_files'), \
                     patch.object(helper, '_client_config_from_env', return_value={}), \
                     patch.object(helper.InstalledAppFlow, 'from_client_config', return_value=flow), \
                     patch.object(helper, '_discover_email', return_value='owner@example.com'), \
                     patch.object(helper, '_write_credentials') as write, \
                     patch.object(helper, '_update_env_file') as update, \
                     patch('builtins.print'), \
                     patch('sys.argv', ['helper', '--profile', profile, '--credentials-dir', directory]):
                    self.assertEqual(helper.main(), 0)
                    self.assertEqual(flow.run_local_server.call_args.kwargs['include_granted_scopes'], include_granted)
                    self.assertEqual(write.call_args.args[0], Path(directory).resolve() / 'owner@example.com.json')
                    self.assertEqual(set(update.call_args.args[1]), {variable, 'GOOGLE_DEFAULT_USER_EMAIL'})
