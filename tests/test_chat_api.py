from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
from fastapi.testclient import TestClient

import backend.main as api_module
from src.database.workspace_store import WorkspaceStore


def rag_response(*, invalid_trace: bool = False):
    trace = SimpleNamespace(
        analyzer=None,
        retrieval_steps=[],
        reasoning=None,
        validation=None,
        decisions=[object()] if invalid_trace else [],
    )
    return SimpleNamespace(
        answer="A grounded test answer.",
        confidence=Decimal("0.8"),
        exhausted_retries=False,
        citations=[
            SimpleNamespace(
                chunk=SimpleNamespace(
                    source="source.pdf",
                    page=np.int64(3),
                    text="Relevant evidence.",
                ),
                combined_score=np.float32(0.75),
            )
        ],
        trace=trace,
    )


class ChatApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = WorkspaceStore(Path(self.temp_dir.name) / "workspace.sqlite3")
        project_id = self.store.create_project("API tests")
        self.chat_id = self.store.list_chats(project_id=project_id)[0]["chat_id"]
        self.workspace_patch = patch.object(api_module, "workspace", self.store)
        self.workspace_patch.start()
        self.addCleanup(self.workspace_patch.stop)
        self.client = TestClient(api_module.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_chat_saves_response_with_json_compatible_numeric_values(self) -> None:
        orchestrator = SimpleNamespace(run=AsyncMock(return_value=rag_response()))

        with patch.object(api_module, "_chat_runtime", return_value=(None, orchestrator, None, None)):
            response = self.client.post(
                f"/api/chats/{self.chat_id}/messages",
                json={"content": "Explain the evidence."},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["assistant_message"]["content"], "A grounded test answer.")
        self.assertEqual(len(self.store.list_messages(self.chat_id)), 2)
        metadata = response.json()["assistant_message"]["metadata"]
        self.assertEqual(metadata["citations"][0]["page"], 3)
        self.assertEqual(metadata["citations"][0]["score"], 0.75)

    def test_rag_failure_returns_actionable_502_and_does_not_save_assistant(self) -> None:
        orchestrator = SimpleNamespace(run=AsyncMock(side_effect=RuntimeError("provider unavailable")))

        with patch.object(api_module, "_chat_runtime", return_value=(None, orchestrator, None, None)):
            response = self.client.post(
                f"/api/chats/{self.chat_id}/messages",
                json={"content": "Explain the evidence."},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("backend logs", response.json()["detail"])
        self.assertEqual([item["role"] for item in self.store.list_messages(self.chat_id)], ["user"])

    def test_response_serialization_failure_returns_clear_500(self) -> None:
        orchestrator = SimpleNamespace(
            run=AsyncMock(return_value=rag_response(invalid_trace=True))
        )

        with patch.object(api_module, "_chat_runtime", return_value=(None, orchestrator, None, None)):
            response = self.client.post(
                f"/api/chats/{self.chat_id}/messages",
                json={"content": "Explain the evidence."},
            )

        self.assertEqual(response.status_code, 500)
        self.assertIn("could not be saved", response.json()["detail"])
        self.assertEqual([item["role"] for item in self.store.list_messages(self.chat_id)], ["user"])


if __name__ == "__main__":
    unittest.main()
