from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.config.settings import AppSettings
from src.database.workspace_store import WorkspaceStore
from src.frontend.workspace import render_workspace

st.set_page_config(page_title="Workspace test", layout="wide")
data_root = Path(os.environ["AGENTIC_RAG_TEST_DATA"])
settings = AppSettings(
    groq_api_key="",
    data_dir=str(data_root),
    index_dir=str(data_root / "index"),
)
store = WorkspaceStore(data_root / "workspace.sqlite3")
chat_id = store.ensure_default_workspace()
chat = store.get_chat(chat_id)
if chat is None:
    raise RuntimeError("Test chat was not initialized.")
render_workspace(
    store,
    settings,
    Path(__file__).resolve().parents[1],
    chat,
    shared_runtime=None,
    configuration_error="RAG runtime intentionally disabled in this UI test.",
)
