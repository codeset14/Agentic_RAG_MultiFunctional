from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class DeploymentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_api_is_gated_when_workspace_password_is_configured(self) -> None:
        with patch.dict(os.environ, {"WORKSPACE_PASSWORD": "deployment-test-password"}):
            unauthorized = self.client.get("/api/projects")
            authorized = self.client.get(
                "/api/projects",
                headers={"X-Workspace-Password": "deployment-test-password"},
            )
            health = self.client.get("/api/health")

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(health.status_code, 200)


if __name__ == "__main__":
    unittest.main()
