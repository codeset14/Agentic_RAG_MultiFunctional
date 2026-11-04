from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

from src.config.settings import AppSettings, load_settings
from src.core.logging import setup_logging
from src.database.workspace_store import WorkspaceStore
from src.frontend.workspace import render_workspace, seed_legacy_documents

logger = logging.getLogger(__name__)


@st.cache_resource(show_spinner="Loading the RAG models...")
def build_shared_runtime() -> Tuple[Any, Any, Any]:
    settings = load_settings()
    if not settings.groq_api_key:
        raise ValueError("Missing GROQ_API_KEY in the local .env file.")
    if not settings.groq_api_key.startswith("gsk_"):
        raise ValueError("Invalid GROQ_API_KEY format.")
    from src.embeddings.encoder import EmbeddingEncoder
    from src.llm.groq_client import GroqClient
    from src.retrieval.reranker import CrossEncoderReranker

    encoder = EmbeddingEncoder(settings.embedding_model)
    reranker = CrossEncoderReranker(settings.reranker_model)
    llm = GroqClient(settings.groq_api_key, settings.groq_model)
    return encoder, reranker, llm


def _resolve_path(root: Path, configured: str) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else root / path


def main() -> None:
    st.set_page_config(
        page_title="Agentic RAG",
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    root = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=root / ".env", override=True)
    setup_logging(logging.INFO)

    try:
        settings: AppSettings = load_settings()
        data_root = _resolve_path(root, settings.data_dir)
        store = WorkspaceStore(data_root / "workspace.sqlite3")
        legacy_index = _resolve_path(root, settings.index_dir)
        initial_chat_id = store.ensure_default_workspace(
            uses_legacy_index=(
                (legacy_index / "vectors.faiss").is_file()
                and (legacy_index / "chunks.json").is_file()
            )
        )
        initial_chat = store.get_chat(initial_chat_id)
        if initial_chat is None:
            raise RuntimeError("Could not initialize the default conversation.")
        seed_legacy_documents(
            store,
            initial_chat,
            legacy_index if initial_chat["uses_legacy_index"] else (
                data_root / "workspaces" / initial_chat_id / "index"
            ),
        )

        shared_runtime: Optional[Tuple[Any, Any, Any]] = None
        configuration_error: Optional[str] = None
        try:
            shared_runtime = build_shared_runtime()
        except Exception as exc:
            logger.exception("Could not initialize the RAG runtime")
            detail = str(exc)
            if settings.groq_api_key:
                detail = detail.replace(settings.groq_api_key, "[redacted]")
            configuration_error = (
                f"RAG services are unavailable: {detail} "
                "Check the local configuration and model dependencies."
            )

        render_workspace(
            store,
            settings,
            root,
            initial_chat,
            shared_runtime,
            configuration_error,
        )
    except Exception as exc:
        logger.exception("Agentic RAG application startup failed")
        st.error(f"Application startup failed: {exc}")


if __name__ == "__main__":
    main()
