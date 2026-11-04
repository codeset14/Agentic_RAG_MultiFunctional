from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from streamlit.testing.v1 import AppTest
from src.database.workspace_store import WorkspaceStore


class FrontendSmokeTests(unittest.TestCase):
    def test_workspace_renders_without_rag_models(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            with patch.dict(os.environ, {"AGENTIC_RAG_TEST_DATA": data_dir}):
                app = AppTest.from_file(
                    str(Path(__file__).with_name("frontend_smoke_app.py"))
                ).run()
                next(
                    button
                    for button in app.button
                    if button.label == "＋  New Project Chat"
                ).click()
                app.run()
                for page in ("Documents", "Analytics", "Settings"):
                    next(radio for radio in app.radio if radio.key == "active_page").set_value(page)
                    app.run()
                settings_rendered = any("Settings" in item.value for item in app.markdown)
                next(toggle for toggle in app.toggle if toggle.label == "Dark mode").set_value(True)
                app.run()
            store = WorkspaceStore(Path(data_dir) / "workspace.sqlite3")
            chat_count = len(store.list_chats())
            theme = store.get_preference("theme", "Light")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(settings_rendered)
        self.assertEqual(chat_count, 2)
        self.assertEqual(theme, "Dark")


if __name__ == "__main__":
    unittest.main()
