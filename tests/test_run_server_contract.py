import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import run_server


class RunServerContractTests(unittest.TestCase):
    def test_doctor_output_only_reports_supported_auth_helpers(self):
        config = run_server.RuntimeConfig(
            host="127.0.0.1",
            port=3002,
            path="/mcp",
            health_path="/health",
            transport="streamable-http",
        )
        buffer = io.StringIO()

        with patch.dict("os.environ", {"GOOGLE_MCP_CREDENTIALS_DIR": "/tmp/.oauth"}, clear=True), patch.object(
            run_server, "is_server_healthy", return_value=True
        ), redirect_stdout(buffer):
            exit_code = run_server.cmd_doctor(config, None)

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("google_credentials_dir=/tmp/.oauth", output)
        self.assertNotIn("service_account_file=", output)

