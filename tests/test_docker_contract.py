import os
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from urllib.request import urlopen


class DockerContractTests(unittest.TestCase):
    def test_compose_file_is_self_contained_by_default(self):
        content = Path("docker-compose.yml").read_text(encoding="utf-8")

        self.assertNotIn("external: true", content)
        self.assertNotIn("reverse_proxy", content)
        self.assertNotIn("env_file:", content)
        self.assertIn("/health", content)

    def test_docker_compose_health_smoke_when_explicitly_enabled(self):
        if os.getenv("GOOGLE_WORKSPACE_MCP_RUN_DOCKER_TESTS", "").strip().lower() != "true":
            self.skipTest("set GOOGLE_WORKSPACE_MCP_RUN_DOCKER_TESTS=true to run Docker smoke validation")
        if shutil.which("docker") is None:
            self.skipTest("docker is not installed in this environment")

        env = os.environ.copy()
        subprocess.run(
            ["docker", "compose", "down", "--remove-orphans"],
            cwd=Path.cwd(),
            env=env,
            check=False,
        )
        try:
            subprocess.run(
                ["docker", "compose", "up", "-d", "--build", "--remove-orphans"],
                cwd=Path.cwd(),
                env=env,
                check=True,
            )

            deadline = time.time() + 90
            last_error = None
            while time.time() < deadline:
                try:
                    with urlopen("http://127.0.0.1:3002/health", timeout=2) as response:
                        payload = response.read().decode("utf-8")
                    self.assertIn('"status":"ok"', payload.replace(" ", ""))
                    return
                except Exception as exc:  # pragma: no cover - exercised only in opt-in Docker runs
                    last_error = exc
                    time.sleep(2)
            if last_error is not None:
                raise last_error
            self.fail("Docker health endpoint did not become ready before the timeout")
        finally:
            subprocess.run(
                ["docker", "compose", "down", "--remove-orphans"],
                cwd=Path.cwd(),
                env=env,
                check=False,
            )
