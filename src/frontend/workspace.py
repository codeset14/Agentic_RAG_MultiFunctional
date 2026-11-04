from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from src.config.settings import AppSettings
from src.core.models import FinalResponse
from src.database.workspace_store import WorkspaceStore
from src.frontend.styles import inject_theme
from src.orchestration.runtime_factory import build_chat_runtime

logger = logging.getLogger(__name__)
SUPPORTED_TYPES = ["pdf", "txt", "csv"]


def _index_dir(chat: Dict[str, Any], settings: AppSettings, project_root: Path) -> Path:
    if chat["uses_legacy_index"]:
        legacy = Path(settings.index_dir)
        return legacy if legacy.is_absolute() else project_root / legacy
    data = Path(settings.data_dir)
    data_root = data if data.is_absolute() else project_root / data
    return data_root / "workspaces" / chat["chat_id"] / "index"


def seed_legacy_documents(
    store: WorkspaceStore, chat: Dict[str, Any], index_dir: Path
) -> None:
    pref_key = f"legacy_documents_seeded:{chat['chat_id']}"
    if not chat["uses_legacy_index"] or store.get_preference(pref_key, False):
        return
    chunks_path = index_dir / "chunks.json"
    raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8")) if chunks_path.is_file() else []
    sources = sorted({chunk["source"] for chunk in raw_chunks})
    for source in sources:
        extension = Path(source).suffix.lstrip(".").upper() or "INDEXED"
        store.add_document(
            chat_id=chat["chat_id"],
            file_name=source,
            file_type=extension,
            file_size=None,
            storage_path=None,
            status="Indexed",
        )
    store.set_preference(pref_key, True)


def _render_sidebar(store: WorkspaceStore, initial_chat: Dict[str, Any]) -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="display:flex;align-items:center;gap:12px;padding:8px 0 18px">
                <div class="brand-mark">A</div>
                <div><div class="brand-title">Agentic RAG</div>
                    <div class="brand-tagline">Smarter Search. Deeper Insights.</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        projects = store.list_projects()
        if not projects:
            raise RuntimeError("The workspace has no projects.")
        if "active_chat_id" not in st.session_state:
            st.session_state.active_chat_id = initial_chat["chat_id"]
        active_id = st.session_state.get("active_chat_id", initial_chat["chat_id"])
        active = store.get_chat(active_id)
        if not active or active["is_deleted"]:
            active = initial_chat
            st.session_state.active_chat_id = active["chat_id"]

        if st.button("＋  New Project Chat", type="primary", use_container_width=True):
            st.session_state.active_chat_id = store.create_chat(active["project_id"])
            st.session_state.pending_active_page = "Chat"
            st.rerun()

        with st.expander("＋ New project", expanded=False):
            with st.form("new_project_form", clear_on_submit=True):
                project_name = st.text_input("Project name")
                project_description = st.text_input("Description")
                create_project = st.form_submit_button("Create project", use_container_width=True)
            if create_project:
                try:
                    project_id = store.create_project(project_name, project_description)
                    new_chat = store.list_chats(project_id=project_id)[0]
                    st.session_state.active_chat_id = new_chat["chat_id"]
                    st.session_state.pending_active_page = "Chat"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        st.markdown("#### Your Chats")
        section = st.selectbox(
            "Navigation",
            ["All Chats", "Starred Chats", "Shared Chats", "Trash"],
            label_visibility="collapsed",
            key="chat_navigation",
        )
        search = st.text_input("Search chats", placeholder="Search title or messages")

        if section == "Shared Chats":
            st.info("Chat sharing is not configured. Your conversations remain private.")
        else:
            deleted = section == "Trash"
            starred = section == "Starred Chats"
            for project in projects:
                chats = store.list_chats(
                    project_id=project["project_id"],
                    starred=starred,
                    deleted=deleted,
                    search=search,
                )
                if not chats:
                    continue
                with st.expander(
                    f"{project['name']}  ·  {len(chats)}",
                    expanded=project["project_id"] == active["project_id"] or bool(search),
                ):
                    for chat in chats:
                        if deleted:
                            left, right = st.columns([4, 1])
                            with left:
                                st.caption(chat["title"])
                            with right:
                                if st.button("↩", key=f"restore_{chat['chat_id']}", help="Restore chat"):
                                    store.set_chat_deleted(chat["chat_id"], False)
                                    st.rerun()
                            continue

                        title = ("★ " if chat["is_starred"] else "") + chat["title"]
                        title_col, star_col, copy_col, trash_col = st.columns(
                            [5.4, 0.8, 0.8, 0.8], gap="small"
                        )
                        with title_col:
                            if st.button(
                                f"◯  {title}",
                                key=f"select_{chat['chat_id']}",
                                type="primary" if chat["chat_id"] == active["chat_id"] else "secondary",
                                use_container_width=True,
                                help=(
                                    f"{chat['message_count']} messages · "
                                    f"updated {chat['updated_at'][:16].replace('T', ' ')}"
                                ),
                            ):
                                st.session_state.active_chat_id = chat["chat_id"]
                                st.rerun()
                        with star_col:
                            if st.button(
                                "☆" if not chat["is_starred"] else "★",
                                key=f"star_{chat['chat_id']}",
                                help="Star or unstar",
                            ):
                                store.toggle_star(chat["chat_id"])
                                st.rerun()
                        with copy_col:
                            if st.button("⧉", key=f"duplicate_{chat['chat_id']}", help="Duplicate chat"):
                                st.session_state.active_chat_id = store.duplicate_chat(chat["chat_id"])
                                st.rerun()
                        with trash_col:
                            if st.button("×", key=f"trash_{chat['chat_id']}", help="Move to trash"):
                                store.set_chat_deleted(chat["chat_id"])
                                remaining = store.list_chats(project_id=chat["project_id"])
                                if not remaining:
                                    st.session_state.active_chat_id = store.create_chat(chat["project_id"])
                                elif st.session_state.active_chat_id == chat["chat_id"]:
                                    st.session_state.active_chat_id = remaining[0]["chat_id"]
                                st.rerun()

        st.divider()
        profile_col, settings_col = st.columns([4, 1])
        with profile_col:
            st.caption("◉  Local workspace")
        with settings_col:
            if st.button("⚙", key="sidebar_settings", help="Settings"):
                st.session_state.pending_active_page = "Settings"
                st.rerun()
    return st.session_state.active_chat_id


def _render_message(message: Dict[str, Any], store: WorkspaceStore) -> None:
    role = message["role"]
    with st.chat_message(role, avatar="🧠" if role == "assistant" else "🙂"):
        st.markdown(message["content"])
        metadata = message.get("metadata") or {}
        if role == "assistant" and "confidence" in metadata:
            confidence = min(max(float(metadata["confidence"]), 0.0), 1.0)
            st.progress(confidence, text=f"Evidence confidence: {confidence:.0%}")
        if role == "assistant" and metadata.get("citations"):
            with st.expander(f"Sources · {len(metadata['citations'])}", expanded=False):
                for citation in metadata["citations"]:
                    page = citation.get("page")
                    page_text = f" · page {page}" if page else ""
                    st.markdown(
                        f"**{citation.get('source', 'Document')}{page_text}**"
                    )
                    st.caption(citation.get("text", ""))
        if role == "assistant" and metadata.get("trace"):
            with st.expander("Agent trace"):
                st.json(metadata["trace"])
        if role == "assistant":
            with st.expander("Copy response"):
                st.code(message["content"], language=None)
            feedback_key = f"feedback:{message['message_id']}"
            feedback = store.get_preference(feedback_key, None)
            left, right, _ = st.columns([0.55, 0.55, 5])
            with left:
                if st.button("👍", key=f"up_{message['message_id']}", help="Helpful"):
                    store.set_preference(feedback_key, "up")
            with right:
                if st.button("👎", key=f"down_{message['message_id']}", help="Not helpful"):
                    store.set_preference(feedback_key, "down")
            if feedback:
                st.caption("Thanks for the feedback.")
        st.caption(message["created_at"][:16].replace("T", " "))


def _response_metadata(response: FinalResponse) -> Dict[str, Any]:
    trace = response.trace
    return {
        "confidence": response.confidence,
        "citations": [
            {
                "source": item.chunk.source,
                "page": item.chunk.page,
                "score": item.combined_score,
                "text": item.chunk.text[:1200],
            }
            for item in response.citations
        ],
        "trace": {
            "analyzer": trace.analyzer.__dict__ if trace.analyzer else {},
            "retrieval": [
                {
                    "iteration": step.iteration,
                    "query_used": step.query_used,
                    "notes": step.notes,
                    "chunks": [
                        {
                            "source": chunk.chunk.source,
                            "page": chunk.chunk.page,
                            "semantic_score": chunk.semantic_score,
                            "keyword_score": chunk.keyword_score,
                            "rerank_score": chunk.rerank_score,
                            "combined_score": chunk.combined_score,
                        }
                        for chunk in step.chunks
                    ],
                }
                for step in trace.retrieval_steps
            ],
            "reasoning": trace.reasoning.__dict__ if trace.reasoning else {},
            "validation": trace.validation.__dict__ if trace.validation else {},
            "decisions": [decision.__dict__ for decision in trace.decisions],
        },
    }


def _run_query(
    prompt: str,
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
    persist_user: bool = True,
) -> None:
    if not prompt.strip():
        return
    if runtime is None:
        st.error("Chat requires a valid GROQ_API_KEY and the configured RAG models.")
        return
    try:
        if persist_user:
            store.add_message(chat["chat_id"], "user", prompt.strip())
            if chat["title"] == "New Chat":
                store.rename_chat(chat["chat_id"], prompt.strip().splitlines()[0][:48])

        _, orchestrator, _, _ = runtime
        with st.spinner("Searching documents and validating an answer..."):
            response = asyncio.run(orchestrator.run(prompt.strip()))
        store.add_message(
            chat["chat_id"],
            "assistant",
            response.answer,
            _response_metadata(response),
        )
        st.session_state.pop(f"chat_error:{chat['chat_id']}", None)
    except Exception as exc:
        logger.exception("RAG request failed for chat %s", chat["chat_id"])
        error_key = f"chat_error:{chat['chat_id']}"
        detail = str(exc)
        if settings.groq_api_key:
            detail = detail.replace(settings.groq_api_key, "[redacted]")
        st.session_state[error_key] = f"Could not complete the request: {detail}"
        if persist_user:
            st.session_state[error_key] += " Your question was saved and can be retried."
    st.rerun()


def _unique_file_name(file_name: str, existing: set[str]) -> str:
    candidate = Path(file_name).name
    stem, suffix = Path(candidate).stem, Path(candidate).suffix
    version = 2
    while candidate in existing:
        candidate = f"{stem} ({version}){suffix}"
        version += 1
    return candidate


def _upload_documents(
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
    files: Any,
    widget_key: str,
) -> None:
    if not files:
        st.warning("Choose at least one PDF, TXT, or CSV document.")
        return
    if runtime is None:
        st.error("Document indexing requires the configured embedding and reranking models.")
        return

    data_path = Path(settings.data_dir)
    data_root = data_path if data_path.is_absolute() else project_root / data_path
    upload_dir = data_root / "uploads" / chat["chat_id"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    existing = {doc["file_name"] for doc in store.list_documents(chat["chat_id"])}
    staged = []
    paths = []
    try:
        for upload in files:
            file_name = _unique_file_name(upload.name, existing)
            existing.add(file_name)
            extension = Path(file_name).suffix.lower()
            if extension not in {f".{item}" for item in SUPPORTED_TYPES}:
                raise ValueError(f"Unsupported file type: {extension or 'unknown'}")
            content = upload.getvalue()
            storage_file = upload_dir / f"{uuid.uuid4().hex}{extension}"
            storage_file.write_bytes(content)
            document_id = store.add_document(
                chat_id=chat["chat_id"],
                file_name=file_name,
                file_type=extension.lstrip(".").upper(),
                file_size=len(content),
                storage_path=str(storage_file),
                status="Uploaded",
            )
            staged.append((file_name, content))
            paths.append((document_id, storage_file))

        indexing, _, _, _ = runtime
        for document_id, _ in paths:
            store.set_document_status(document_id, "Processing")
        with st.spinner(f"Indexing {len(staged)} document(s)..."):
            indexing.build_from_uploads(staged)
        for document_id, _ in paths:
            store.set_document_status(document_id, "Indexed")
        st.success(f"Indexed {len(staged)} document(s) for this chat.")
        nonce_key = f"upload_nonce:{widget_key}:{chat['chat_id']}"
        st.session_state[nonce_key] = st.session_state.get(nonce_key, 0) + 1
        st.rerun()
    except Exception as exc:
        logger.exception("Document upload/indexing failed for chat %s", chat["chat_id"])
        for document_id, _ in paths:
            store.set_document_status(document_id, "Failed")
        st.error(f"Document processing failed: {exc}")


def _render_upload_control(
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
    key_prefix: str,
) -> None:
    nonce_key = f"upload_nonce:{key_prefix}:{chat['chat_id']}"
    nonce = st.session_state.get(nonce_key, 0)
    uploader_key = f"{key_prefix}_{chat['chat_id']}_{nonce}"
    uploads = st.file_uploader(
        "Add documents to this chat",
        type=SUPPORTED_TYPES,
        accept_multiple_files=True,
        key=uploader_key,
        help="Supported by the current ingestion pipeline: PDF, TXT, and CSV.",
    )
    if st.button("Upload & index", key=f"upload_button_{uploader_key}", use_container_width=True):
        _upload_documents(
            chat, store, settings, project_root, runtime, uploads, key_prefix
        )


def _delete_document(
    document: Dict[str, Any],
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
) -> None:
    index_dir = _index_dir(chat, settings, project_root)
    from src.retrieval.faiss_store import FaissStore

    index = FaissStore(str(index_dir))
    index.load()
    index.remove_sources({document["file_name"]})
    removed = store.delete_document(document["document_id"])
    if removed["storage_path"]:
        path = Path(removed["storage_path"])
        if path.is_file():
            path.unlink()
    st.rerun()


def _document_preview(document: Dict[str, Any]) -> None:
    if not document["storage_path"]:
        st.info("This document is part of the pre-existing index; its original file is not available to preview.")
        return
    path = Path(document["storage_path"])
    if not path.is_file():
        st.error("The stored file is missing. Remove it and upload it again.")
        return
    try:
        from src.ingestion.loaders import load_document

        pages = load_document(path.read_bytes(), document["file_name"])
        text = "\n\n".join(f"Page {page}: {content}" for content, page in pages)
        st.text_area("Document preview", text[:12000], height=260, disabled=True)
    except Exception as exc:
        logger.exception("Could not preview document %s", document["file_name"])
        st.error(f"Preview failed: {exc}")


def _render_documents(
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
) -> None:
    st.markdown('<div class="page-heading">Documents</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Documents associated with the selected chat.</div>', unsafe_allow_html=True)
    st.caption(chat["title"])
    _render_upload_control(chat, store, settings, project_root, runtime, "documents")
    documents = store.list_documents(chat["chat_id"])
    filter_col, search_col = st.columns([1, 2])
    with filter_col:
        file_type = st.selectbox(
            "File type", ["All types"] + sorted({doc["file_type"] for doc in documents})
        )
    with search_col:
        search = st.text_input("Search documents", placeholder="Find a filename")
    visible = [
        doc for doc in documents
        if (file_type == "All types" or doc["file_type"] == file_type)
        and search.casefold() in doc["file_name"].casefold()
    ]
    if not visible:
        st.info("No documents match this chat and filter.")
    for document in visible:
        with st.expander(f"{document['file_name']} · {document['processing_status']}"):
            size = (
                f"{document['file_size'] / 1024:.1f} KB"
                if document["file_size"] is not None
                else "Size unavailable"
            )
            st.caption(
                f"{document['file_type']} · {size} · "
                f"added {document['uploaded_at'][:10]}"
            )
            preview_col, delete_col = st.columns([1, 1])
            with preview_col:
                if st.button("Preview", key=f"preview_doc_{document['document_id']}"):
                    st.session_state[f"preview_doc:{document['document_id']}"] = True
            with delete_col:
                if st.button("Delete", key=f"delete_doc_{document['document_id']}"):
                    try:
                        _delete_document(document, chat, store, settings, project_root)
                    except Exception as exc:
                        logger.exception("Could not delete document %s", document["document_id"])
                        st.error(f"Document deletion failed: {exc}")
            if st.session_state.get(f"preview_doc:{document['document_id']}"):
                _document_preview(document)


def _render_context_content(
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
) -> None:
    if not st.toggle("Show chat context", value=st.session_state.get("show_context", True)):
        st.session_state.show_context = False
        return
    st.session_state.show_context = True
    documents = store.list_documents(chat["chat_id"])
    messages = store.list_messages(chat["chat_id"])
    project = next(
        (item for item in store.list_projects() if item["project_id"] == chat["project_id"]),
        None,
    )
    project_chats = store.list_chats(project_id=chat["project_id"])
    project_documents = sum(
        len(store.list_documents(project_chat["chat_id"])) for project_chat in project_chats
    )
    st.markdown("#### Chat details")
    st.caption(chat["project_name"])
    st.markdown(f"**{chat['title']}**")
    st.caption(
        f"{len(messages)} messages · {len(documents)} documents · "
        f"active {chat['updated_at'][:16].replace('T', ' ')}"
    )
    with st.expander("Project overview", expanded=False):
        if project:
            st.caption(project["description"] or "No project description.")
        st.caption(
            f"{len(project_chats)} conversations · {project_documents} documents · "
            f"recent activity {chat['updated_at'][:10]}"
        )

    with st.expander("Manage chat", expanded=False):
        with st.form(f"rename_chat_{chat['chat_id']}"):
            title = st.text_input("Chat title", value=chat["title"])
            if st.form_submit_button("Save title"):
                try:
                    store.rename_chat(chat["chat_id"], title)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        if st.button("Duplicate conversation", key=f"context_duplicate_{chat['chat_id']}"):
            st.session_state.active_chat_id = store.duplicate_chat(chat["chat_id"])
            st.rerun()
        clear_key = f"confirm_clear:{chat['chat_id']}"
        if st.button("Clear conversation history", key=f"clear_history_{chat['chat_id']}"):
            st.session_state[clear_key] = True
        if st.session_state.get(clear_key):
            st.warning("This removes messages from this chat but keeps its documents.")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button("Confirm clear", key=f"confirm_clear_button_{chat['chat_id']}"):
                    store.clear_messages(chat["chat_id"])
                    st.session_state.pop(clear_key, None)
                    st.session_state.pop(f"chat_error:{chat['chat_id']}", None)
                    st.rerun()
            with cancel_col:
                if st.button("Cancel", key=f"cancel_clear_{chat['chat_id']}"):
                    st.session_state.pop(clear_key, None)
                    st.rerun()
        if st.button("Move conversation to Trash", key=f"context_delete_{chat['chat_id']}"):
            store.set_chat_deleted(chat["chat_id"])
            remaining = store.list_chats(project_id=chat["project_id"])
            st.session_state.active_chat_id = (
                remaining[0]["chat_id"] if remaining else store.create_chat(chat["project_id"])
            )
            st.rerun()

    st.markdown("#### This chat's documents")
    if not documents:
        st.caption("No documents attached.")
    for document in documents[:5]:
        file_icon = {"PDF": "📕", "TXT": "📄", "CSV": "📊"}.get(
            document["file_type"], "📄"
        )
        st.markdown(f"{file_icon} **{document['file_name']}**")
        st.caption(f"{document['file_type']} · {document['processing_status']}")
    if len(documents) > 5:
        st.caption(f"+ {len(documents) - 5} more · see Documents")
    if st.button("View all documents →", key=f"view_docs_{chat['chat_id']}"):
        st.session_state.pending_active_page = "Documents"
        st.rerun()

    st.markdown("#### Quick actions")
    actions = [
        ("Summarize", "Summarize the key information in the documents indexed for this chat."),
        ("Study plan", "Create a practical study plan based on the documents indexed for this chat."),
        ("Create quiz", "Create a short quiz with answers based on the documents indexed for this chat."),
        ("Write code", "Write code relevant to the documents indexed for this chat. Explain assumptions."),
        ("Analyze data", "Analyze the data in the documents indexed for this chat and report evidence."),
    ]
    for row in range(0, len(actions), 2):
        cols = st.columns(2)
        for col, (label, prompt) in zip(cols, actions[row:row + 2]):
            with col:
                if st.button(label, key=f"quick_{label}_{chat['chat_id']}", use_container_width=True):
                    st.session_state.queued_prompt = prompt
                    st.session_state.pending_active_page = "Chat"
                    st.rerun()
    st.button("Search web · not configured", disabled=True, use_container_width=True)


def _render_context(
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
) -> None:
    with st.container(border=True, key="right_context"):
        _render_context_content(chat, store, settings, project_root, runtime)


def _render_chat(
    chat: Dict[str, Any],
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    runtime: Optional[Tuple[Any, Any, Any, Any]],
    configuration_error: Optional[str],
) -> None:
    if configuration_error:
        with st.expander("⚠ RAG services need setup"):
            st.warning(configuration_error)

    messages = store.list_messages(chat["chat_id"])
    if not messages:
        st.markdown(
            """
            <div class="welcome-card">
                <span class="welcome-sparkle">✦</span>
                <div class="welcome-robot" aria-hidden="true">🤖</div>
                <h2>Welcome to Agentic RAG!</h2>
                <p>Ask anything, explore your documents, and let the agent handle the rest.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        prompts = [
            ("Search your documents", "Find the most relevant information in this chat's documents."),
            ("Run analysis", "Analyze the key facts and themes in this chat's indexed documents."),
            ("Write code", "Help me write code using relevant evidence from this chat's documents."),
            ("Get insights", "Identify useful insights grounded in this chat's indexed documents."),
        ]
        for col, (label, prompt) in zip(cols, prompts):
            with col:
                if st.button(label, key=f"welcome_{label}_{chat['chat_id']}", use_container_width=True):
                    st.session_state.queued_prompt = prompt
                    st.rerun()
    for message in messages:
        _render_message(message, store)

    chat_error = st.session_state.get(f"chat_error:{chat['chat_id']}")
    if chat_error:
        st.error(chat_error)
        if messages and messages[-1]["role"] == "user":
            if st.button("Retry last question", key=f"retry_{chat['chat_id']}"):
                _run_query(
                    messages[-1]["content"], chat, store, settings, runtime, persist_user=False
                )

    if runtime is not None and messages and messages[-1]["role"] == "assistant":
        if st.button("Regenerate response", key=f"regenerate_{messages[-1]['message_id']}"):
            previous_user = next(
                (message for message in reversed(messages[:-1]) if message["role"] == "user"),
                None,
            )
            if previous_user:
                _run_query(
                    previous_user["content"], chat, store, settings, runtime, persist_user=False
                )

    chat_documents = store.list_documents(chat["chat_id"])
    selected_document = "No mention"
    attach_col, tools_col = st.columns([1, 1])
    with attach_col:
        with st.popover("📎 Attach", help="Upload documents to this chat"):
            _render_upload_control(chat, store, settings, project_root, runtime, "chat")
    with tools_col:
        with st.popover("✨ Tools", help="Choose a document and chat tool"):
            st.caption("Document search is enabled for this chat.")
            selected_document = st.selectbox(
                "Mention a document",
                ["No mention"] + [document["file_name"] for document in chat_documents],
                key=f"mention_{chat['chat_id']}",
            )
            st.toggle(
                "Web search",
                value=False,
                disabled=True,
                help="Web search is not configured.",
            )
    query = st.chat_input("Ask anything about this chat's documents...")
    queued = st.session_state.pop("queued_prompt", None)
    if queued:
        query = queued
    if query:
        if selected_document != "No mention":
            query = f"@{selected_document}\n{query}"
        _run_query(query, chat, store, settings, runtime)


def _render_analytics(store: WorkspaceStore) -> None:
    st.markdown('<div class="page-heading">Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Usage from this local workspace.</div>', unsafe_allow_html=True)
    analytics = store.analytics()
    counts = analytics["counts"]
    columns = st.columns(5)
    labels = [
        ("Projects", counts["projects"]),
        ("Conversations", counts["conversations"]),
        ("Messages", counts["messages"]),
        ("Documents", counts["documents"]),
        ("Indexed", counts["indexed_documents"]),
    ]
    for column, (label, value) in zip(columns, labels):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    daily: Dict[str, int] = {}
    for item in analytics["activity"]:
        day = item["timestamp"][:10]
        daily[day] = daily.get(day, 0) + 1
    st.markdown("#### Recent activity")
    if daily:
        st.bar_chart({"Activity": daily})
    else:
        st.info("Activity will appear here as you chat and index documents.")
    if analytics["activity"]:
        st.dataframe(analytics["activity"], use_container_width=True, hide_index=True)


def _render_settings(
    store: WorkspaceStore,
    settings: AppSettings,
) -> bool:
    st.markdown('<div class="page-heading">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Preferences for this local workspace.</div>', unsafe_allow_html=True)
    saved_theme = store.get_preference("theme", "Light")
    saved_top_k = int(store.get_preference("top_k", settings.top_k))
    saved_iterations = int(store.get_preference("max_iterations", settings.max_iterations))
    with st.form("settings_form"):
        theme = st.selectbox("Appearance", ["Light", "Dark"], index=0 if saved_theme == "Light" else 1)
        top_k = st.slider("Retrieval results (Top-K)", 3, 20, min(max(saved_top_k, 3), 20))
        max_iterations = st.slider(
            "Maximum validation iterations", 1, 6, min(max(saved_iterations, 1), 6)
        )
        save = st.form_submit_button("Save preferences", type="primary")
    if save:
        store.set_preference("theme", theme)
        store.set_preference("top_k", top_k)
        store.set_preference("max_iterations", max_iterations)
        st.success("Preferences saved.")
        return True

    st.markdown("#### Model and RAG configuration")
    st.caption(f"LLM: {settings.groq_model}")
    st.caption(f"Embeddings: {settings.embedding_model}")
    st.caption(f"Reranker: {settings.reranker_model}")
    st.caption("API credentials are read from the local .env file and are never displayed here.")
    st.caption("Supported document ingestion: PDF, TXT, CSV.")
    st.caption("Web search, account management, and chat sharing are not configured.")
    return False


def render_workspace(
    store: WorkspaceStore,
    settings: AppSettings,
    project_root: Path,
    initial_chat: Dict[str, Any],
    shared_runtime: Optional[Tuple[Any, Any, Any]],
    configuration_error: Optional[str] = None,
) -> None:
    pending_page = st.session_state.pop("pending_active_page", None)
    if pending_page:
        st.session_state.active_page = pending_page
    dark = store.get_preference("theme", "Light") == "Dark"
    inject_theme(dark)
    chat_id = _render_sidebar(store, initial_chat)
    chat = store.get_chat(chat_id)
    if not chat or chat["is_deleted"]:
        raise RuntimeError("The selected conversation is unavailable.")

    top_k = int(store.get_preference("top_k", settings.top_k))
    iterations = int(store.get_preference("max_iterations", settings.max_iterations))
    runtime: Optional[Tuple[Any, Any, Any, Any]] = None
    if shared_runtime is not None:
        encoder, reranker, llm = shared_runtime
        history = store.list_messages(chat_id)
        runtime = build_chat_runtime(
            settings,
            _index_dir(chat, settings, project_root),
            history,
            encoder,
            reranker,
            llm,
            top_k,
            iterations,
        )

    nav_col, theme_col, version_col = st.columns([4.3, 0.9, 1.15])
    with nav_col:
        st.radio(
            "Dashboard",
            ["Chat", "Documents", "Analytics", "Settings"],
            horizontal=True,
            label_visibility="collapsed",
            key="active_page",
        )
    with theme_col:
        selected_dark_theme = st.toggle(
            "Dark mode", value=dark, key=f"theme_toggle_{dark}"
        )
    if selected_dark_theme != dark:
        store.set_preference("theme", "Dark" if selected_dark_theme else "Light")
        st.rerun()
    with version_col:
        status_text = "● RAG ready" if shared_runtime is not None else "● Setup needed"
        st.markdown(
            f'<div class="version-pill">{status_text} · v1.0</div>',
            unsafe_allow_html=True,
        )
    page = st.session_state.active_page

    main_col, context_col = st.columns([2.4, 1], gap="large")
    with main_col:
        if page == "Chat":
            _render_chat(
                chat, store, settings, project_root, runtime, configuration_error
            )
        elif page == "Documents":
            if configuration_error:
                st.warning(configuration_error)
            _render_documents(chat, store, settings, project_root, runtime)
        elif page == "Analytics":
            _render_analytics(store)
        else:
            if _render_settings(store, settings):
                st.rerun()
    with context_col:
        _render_context(chat, store, settings, project_root, runtime)
