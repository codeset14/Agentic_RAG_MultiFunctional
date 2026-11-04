from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.database.workspace_store import WorkspaceStore


class WorkspaceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "workspace.sqlite3"
        self.store = WorkspaceStore(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_chat_history_and_documents_are_isolated_and_persistent(self) -> None:
        project_id = self.store.create_project("Research")
        first_chat = self.store.list_chats(project_id=project_id)[0]["chat_id"]
        second_chat = self.store.create_chat(project_id)
        self.store.add_message(first_chat, "user", "First chat question")
        self.store.add_document(
            first_chat, "research.txt", "TXT", 18, "uploads/research.txt", "Indexed"
        )

        reopened = WorkspaceStore(self.database_path)
        self.assertEqual(
            [message["content"] for message in reopened.list_messages(first_chat)],
            ["First chat question"],
        )
        self.assertEqual(len(reopened.list_documents(first_chat)), 1)
        self.assertEqual(reopened.list_messages(second_chat), [])
        self.assertEqual(reopened.list_documents(second_chat), [])

    def test_star_duplicate_and_trash_restore(self) -> None:
        chat_id = self.store.ensure_default_workspace()
        self.store.add_message(chat_id, "user", "Keep this history")
        self.assertTrue(self.store.toggle_star(chat_id))

        duplicate_id = self.store.duplicate_chat(chat_id)
        self.assertEqual(len(self.store.list_messages(duplicate_id)), 1)
        self.assertEqual(self.store.list_documents(duplicate_id), [])
        self.store.set_chat_deleted(chat_id)
        self.assertEqual(self.store.list_chats(deleted=True)[0]["chat_id"], chat_id)
        self.store.set_chat_deleted(chat_id, False)
        self.assertEqual(len(self.store.list_chats()), 2)

    def test_analytics_counts_real_records(self) -> None:
        chat_id = self.store.ensure_default_workspace()
        self.store.add_message(chat_id, "user", "Count me")
        self.store.add_document(chat_id, "notes.csv", "CSV", 12, "notes.csv", "Indexed")

        counts = self.store.analytics()["counts"]
        self.assertEqual(counts["projects"], 1)
        self.assertEqual(counts["conversations"], 1)
        self.assertEqual(counts["messages"], 1)
        self.assertEqual(counts["documents"], 1)
        self.assertEqual(counts["indexed_documents"], 1)

    def test_clearing_history_keeps_chat_documents(self) -> None:
        chat_id = self.store.ensure_default_workspace()
        self.store.add_message(chat_id, "user", "Forget the messages")
        self.store.add_document(chat_id, "keep.txt", "TXT", 4, "keep.txt", "Indexed")

        self.store.clear_messages(chat_id)

        self.assertEqual(self.store.list_messages(chat_id), [])
        self.assertEqual(len(self.store.list_documents(chat_id)), 1)

    def test_replacing_deleted_default_chat_does_not_reuse_legacy_index(self) -> None:
        legacy_chat_id = self.store.ensure_default_workspace(uses_legacy_index=True)
        self.store.set_chat_deleted(legacy_chat_id)

        replacement_id = self.store.ensure_default_workspace(uses_legacy_index=True)

        self.assertNotEqual(replacement_id, legacy_chat_id)
        self.assertFalse(self.store.get_chat(replacement_id)["uses_legacy_index"])

    def test_project_trash_hides_and_restores_its_conversations(self) -> None:
        project_id = self.store.create_project("Archive me")
        chat_id = self.store.list_chats(project_id=project_id)[0]["chat_id"]

        self.store.set_project_deleted(project_id)

        self.assertNotIn(project_id, [item["project_id"] for item in self.store.list_projects()])
        self.assertIn(
            project_id,
            [item["project_id"] for item in self.store.list_projects(include_deleted=True)],
        )
        self.assertEqual(self.store.list_chats(deleted=True)[0]["chat_id"], chat_id)

        self.store.set_project_deleted(project_id, False)

        self.assertIn(project_id, [item["project_id"] for item in self.store.list_projects()])
        self.assertEqual(
            self.store.list_chats(project_id=project_id)[0]["chat_id"], chat_id
        )


if __name__ == "__main__":
    unittest.main()
