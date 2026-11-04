from __future__ import annotations

import asyncio
import logging
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from src.config.settings import AppSettings, load_settings
from src.database.workspace_store import WorkspaceStore
from src.orchestration.runtime_factory import build_chat_runtime

logger = logging.getLogger("agentic_rag.api")
settings: AppSettings = load_settings()
configured_data = Path(settings.data_dir)
DATA_ROOT = configured_data if configured_data.is_absolute() else ROOT / configured_data
workspace = WorkspaceStore(DATA_ROOT / "workspace.sqlite3")

legacy_index = Path(settings.index_dir)
legacy_index = legacy_index if legacy_index.is_absolute() else ROOT / legacy_index
default_chat_id = workspace.ensure_default_workspace(
    uses_legacy_index=(
        (legacy_index / "vectors.faiss").is_file()
        and (legacy_index / "chunks.json").is_file()
    )
)

app = FastAPI(title="Agentic RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)


class ChatCreate(BaseModel):
    project_id: str
    title: str = Field(default="New Chat", max_length=120)


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    project_id: Optional[str] = None
    is_starred: Optional[bool] = None
    is_deleted: Optional[bool] = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


class PreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=3, le=20)
    max_iterations: Optional[int] = Field(default=None, ge=1, le=6)


class FeedbackUpdate(BaseModel):
    feedback: str


def _index_dir(chat: Dict[str, Any]) -> Path:
    if chat["uses_legacy_index"]:
        return legacy_index
    return DATA_ROOT / "workspaces" / chat["chat_id"] / "index"


@lru_cache(maxsize=1)
def _shared_runtime() -> tuple[Any, Any, Any]:
    try:
        from src.embeddings.encoder import EmbeddingEncoder
        from src.llm.groq_client import GroqClient
        from src.retrieval.reranker import CrossEncoderReranker

        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is missing from .env.")
        return (
            EmbeddingEncoder(settings.embedding_model),
            CrossEncoderReranker(settings.reranker_model),
            GroqClient(settings.groq_api_key, settings.groq_model),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG services are unavailable. Configure GROQ_API_KEY and install "
                f"the required model dependencies. ({exc})"
            ),
        ) from exc


def _chat_runtime(chat_id: str) -> tuple[Any, Any, Any, Any]:
    chat = workspace.get_chat(chat_id)
    if not chat or chat["is_deleted"]:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    encoder, reranker, llm = _shared_runtime()
    top_k = int(workspace.get_preference("top_k", settings.top_k))
    iterations = int(workspace.get_preference("max_iterations", settings.max_iterations))
    return build_chat_runtime(
        settings,
        _index_dir(chat),
        workspace.list_messages(chat_id),
        encoder,
        reranker,
        llm,
        top_k,
        iterations,
    )


def _require_chat(chat_id: str) -> Dict[str, Any]:
    chat = workspace.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if chat["is_deleted"]:
        raise HTTPException(status_code=409, detail="Conversation is in Trash.")
    return chat


def _handle_value_error(operation):
    try:
        return operation()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _seed_legacy_documents() -> None:
    chat = workspace.get_chat(default_chat_id)
    if not chat or not chat["uses_legacy_index"]:
        return
    preference_key = f"legacy_documents_seeded:{default_chat_id}"
    if workspace.get_preference(preference_key, False):
        return
    chunks_path = legacy_index / "chunks.json"
    if chunks_path.is_file():
        import json

        source_names = sorted(
            {item["source"] for item in json.loads(chunks_path.read_text(encoding="utf-8"))}
        )
        for source in source_names:
            workspace.add_document(
                default_chat_id,
                source,
                Path(source).suffix.lstrip(".").upper() or "INDEXED",
                None,
                None,
                "Indexed",
            )
    workspace.set_preference(preference_key, True)


_seed_legacy_documents()


@app.get("/api/health")
def health() -> Dict[str, Any]:
    dependencies: Dict[str, bool] = {}
    for package, module in (
        ("groq", "groq"),
        ("sentence-transformers", "sentence_transformers"),
        ("faiss-cpu", "faiss"),
    ):
        try:
            from importlib.util import find_spec

            dependencies[package] = find_spec(module) is not None
        except (ImportError, ValueError):
            dependencies[package] = False
    return {
        "status": "ok",
        "rag_ready": all(dependencies.values()) and bool(settings.groq_api_key),
        "dependencies": dependencies,
        "has_groq_key": bool(settings.groq_api_key),
        "model": settings.groq_model,
    }


@app.get("/api/projects")
def list_projects() -> List[Dict[str, Any]]:
    return workspace.list_projects()


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate) -> Dict[str, Any]:
    try:
        project_id = workspace.create_project(payload.name, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return next(project for project in workspace.list_projects() if project["project_id"] == project_id)


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate) -> Dict[str, Any]:
    _handle_value_error(
        lambda: workspace.update_project(
            project_id, name=payload.name, description=payload.description
        )
    )
    return next(
        (project for project in workspace.list_projects() if project["project_id"] == project_id),
        {},
    )


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    _handle_value_error(lambda: workspace.set_project_deleted(project_id))


@app.get("/api/projects/trash")
def list_deleted_projects() -> List[Dict[str, Any]]:
    return [project for project in workspace.list_projects(include_deleted=True) if project["is_deleted"]]


@app.post("/api/projects/{project_id}/restore")
def restore_project(project_id: str) -> Dict[str, Any]:
    _handle_value_error(lambda: workspace.set_project_deleted(project_id, False))
    return next(
        project
        for project in workspace.list_projects()
        if project["project_id"] == project_id
    )


@app.get("/api/chats")
def list_chats(
    project_id: Optional[str] = None,
    starred: bool = False,
    deleted: bool = False,
    search: str = "",
) -> List[Dict[str, Any]]:
    return workspace.list_chats(
        project_id=project_id,
        starred=starred,
        deleted=deleted,
        search=search,
    )


@app.post("/api/chats", status_code=201)
def create_chat(payload: ChatCreate) -> Dict[str, Any]:
    try:
        chat_id = workspace.create_chat(payload.project_id, payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return workspace.get_chat(chat_id) or {}


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str) -> Dict[str, Any]:
    chat = workspace.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = workspace.list_messages(chat_id)
    return {
        **chat,
        "message_count": len(messages),
        "messages": messages,
        "documents": workspace.list_documents(chat_id),
    }


@app.patch("/api/chats/{chat_id}")
def update_chat(chat_id: str, payload: ChatUpdate) -> Dict[str, Any]:
    chat = workspace.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    try:
        if payload.project_id is not None:
            workspace.move_chat(chat_id, payload.project_id)
        if payload.title is not None:
            workspace.rename_chat(chat_id, payload.title)
        if payload.is_starred is not None:
            current = bool(workspace.get_chat(chat_id)["is_starred"])
            if current != payload.is_starred:
                workspace.toggle_star(chat_id)
        if payload.is_deleted is not None:
            workspace.set_chat_deleted(chat_id, payload.is_deleted)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return workspace.get_chat(chat_id) or {}


@app.delete("/api/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: str) -> None:
    _handle_value_error(lambda: workspace.set_chat_deleted(chat_id))


@app.post("/api/chats/{chat_id}/restore")
def restore_chat(chat_id: str) -> Dict[str, Any]:
    _handle_value_error(lambda: workspace.set_chat_deleted(chat_id, False))
    return workspace.get_chat(chat_id) or {}


@app.post("/api/chats/{chat_id}/duplicate", status_code=201)
def duplicate_chat(chat_id: str) -> Dict[str, Any]:
    try:
        duplicate_id = workspace.duplicate_chat(chat_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return workspace.get_chat(duplicate_id) or {}


@app.get("/api/chats/{chat_id}/messages")
def list_messages(chat_id: str) -> List[Dict[str, Any]]:
    _require_chat(chat_id)
    return workspace.list_messages(chat_id)


@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: str, payload: MessageCreate) -> Dict[str, Any]:
    chat = _require_chat(chat_id)
    question = payload.content.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")
    user_message_id = workspace.add_message(chat_id, "user", question)
    if chat["title"] == "New Chat":
        workspace.rename_chat(chat_id, question.splitlines()[0][:48])

    try:
        _, orchestrator, _, _ = _chat_runtime(chat_id)
        response = await orchestrator.run(question)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("RAG request failed for conversation %s", chat_id)
        raise HTTPException(status_code=502, detail="RAG request failed. Check backend logs.") from exc

    try:
        metadata = {
            "confidence": float(response.confidence),
            "exhausted_retries": response.exhausted_retries,
            "citations": [
                {
                    "source": item.chunk.source,
                    "page": item.chunk.page,
                    "score": float(item.combined_score),
                    "text": item.chunk.text[:1200],
                }
                for item in response.citations
            ],
            "trace": {
                "analyzer": response.trace.analyzer.__dict__ if response.trace.analyzer else {},
                "retrieval": [
                    {
                        "iteration": step.iteration,
                        "query_used": step.query_used,
                        "notes": step.notes,
                    }
                    for step in response.trace.retrieval_steps
                ],
                "reasoning": response.trace.reasoning.__dict__ if response.trace.reasoning else {},
                "validation": response.trace.validation.__dict__ if response.trace.validation else {},
                "decisions": [decision.__dict__ for decision in response.trace.decisions],
            },
        }
        assistant_id = workspace.add_message(
            chat_id, "assistant", response.answer, metadata
        )
        assistant_message = next(
            message
            for message in workspace.list_messages(chat_id)
            if message["message_id"] == assistant_id
        )
    except Exception as exc:
        logger.exception("Could not serialize or save RAG response for conversation %s", chat_id)
        raise HTTPException(
            status_code=500,
            detail="The answer was generated but could not be saved. Check backend logs.",
        ) from exc

    return {
        "user_message_id": user_message_id,
        "assistant_message": assistant_message,
    }


@app.post("/api/messages/{message_id}/feedback", status_code=204)
def set_feedback(message_id: str, payload: FeedbackUpdate) -> None:
    try:
        workspace.set_message_feedback(message_id, payload.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/chats/{chat_id}/documents")
def list_documents(chat_id: str) -> List[Dict[str, Any]]:
    _require_chat(chat_id)
    return workspace.list_documents(chat_id)


@app.post("/api/chats/{chat_id}/documents", status_code=201)
async def upload_documents(
    chat_id: str, files: List[UploadFile] = File(...)
) -> List[Dict[str, Any]]:
    _require_chat(chat_id)
    if not files:
        raise HTTPException(status_code=422, detail="Upload at least one PDF, TXT, or CSV.")

    upload_dir = DATA_ROOT / "uploads" / chat_id
    existing = {document["file_name"] for document in workspace.list_documents(chat_id)}
    staged: List[tuple[str, bytes, int]] = []
    for upload in files:
        extension = Path(upload.filename or "").suffix.lower()
        if extension not in {".pdf", ".txt", ".csv"}:
            raise HTTPException(
                status_code=415,
                detail=f"{upload.filename or 'File'}: supported formats are PDF, TXT, and CSV.",
            )
        base_name = Path(upload.filename or "document").name
        candidate = base_name
        stem, suffix = Path(base_name).stem, Path(base_name).suffix
        counter = 2
        while candidate in existing:
            candidate = f"{stem} ({counter}){suffix}"
            counter += 1
        existing.add(candidate)
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=422, detail=f"{candidate} is empty.")
        staged.append((candidate, content, len(content)))

    try:
        indexing, _, _, _ = _chat_runtime(chat_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not initialize document indexing for %s", chat_id)
        raise HTTPException(status_code=503, detail="Document indexing is unavailable.") from exc

    upload_dir.mkdir(parents=True, exist_ok=True)
    staged_uploads: List[tuple[str, bytes]] = []
    added_ids: List[str] = []
    for candidate, content, size in staged:
        extension = Path(candidate).suffix.lower()
        path = upload_dir / f"{uuid.uuid4().hex}{extension}"
        path.write_bytes(content)
        document_id = workspace.add_document(
            chat_id,
            candidate,
            extension.lstrip(".").upper(),
            size,
            str(path),
            "Uploaded",
        )
        added_ids.append(document_id)
        staged_uploads.append((candidate, content))

    for document_id in added_ids:
        workspace.set_document_status(document_id, "Processing")
    try:
        await asyncio.to_thread(indexing.build_from_uploads, staged_uploads)
    except Exception as exc:
        logger.exception("Document indexing failed for conversation %s", chat_id)
        for document_id in added_ids:
            workspace.set_document_status(document_id, "Failed")
        raise HTTPException(status_code=422, detail="Indexing failed; check file contents and logs.") from exc
    for document_id in added_ids:
        workspace.set_document_status(document_id, "Indexed")
    return workspace.list_documents(chat_id)


@app.get("/api/documents/{document_id}/preview")
def preview_document(document_id: str) -> Dict[str, Any]:
    document = next(
        (
            item
            for chat in workspace.list_chats()
            for item in workspace.list_documents(chat["chat_id"])
            if item["document_id"] == document_id
        ),
        None,
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not document["storage_path"]:
        raise HTTPException(status_code=410, detail="The original file is not available.")
    path = Path(document["storage_path"]).resolve()
    if not path.is_relative_to((DATA_ROOT / "uploads").resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="Document file is missing.")
    try:
        from src.ingestion.loaders import load_document

        pages = load_document(path.read_bytes(), document["file_name"])
    except Exception as exc:
        logger.exception("Document preview failed: %s", document_id)
        raise HTTPException(status_code=422, detail="Document could not be previewed.") from exc
    return {
        "document_id": document_id,
        "file_name": document["file_name"],
        "text": "\n\n".join(f"Page {page}: {text}" for text, page in pages)[:20000],
    }


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document(document_id: str) -> None:
    document = next(
        (
            (chat, item)
            for chat in workspace.list_chats()
            for item in workspace.list_documents(chat["chat_id"])
            if item["document_id"] == document_id
        ),
        None,
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    chat, item = document
    try:
        from src.retrieval.faiss_store import FaissStore

        index = FaissStore(str(_index_dir(chat)))
        index.load()
        index.remove_sources({item["file_name"]})
    except Exception as exc:
        logger.exception("Could not remove document from retrieval index: %s", document_id)
        raise HTTPException(status_code=503, detail="Could not update the document index.") from exc
    removed = workspace.delete_document(document_id)
    if removed["storage_path"]:
        file_path = Path(removed["storage_path"])
        if file_path.is_file():
            file_path.unlink()


@app.get("/api/analytics")
def analytics() -> Dict[str, Any]:
    result = workspace.analytics()
    documents = [
        document
        for chat in workspace.list_chats()
        for document in workspace.list_documents(chat["chat_id"])
    ]
    type_counts: Dict[str, int] = {}
    for document in documents:
        type_counts[document["file_type"]] = type_counts.get(document["file_type"], 0) + 1
    return {
        **result,
        "document_types": [
            {"type": file_type, "count": count}
            for file_type, count in sorted(type_counts.items())
        ],
    }


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    return {
        "theme": workspace.get_preference("theme", "Light"),
        "top_k": int(workspace.get_preference("top_k", settings.top_k)),
        "max_iterations": int(
            workspace.get_preference("max_iterations", settings.max_iterations)
        ),
        "model": settings.groq_model,
        "embedding_model": settings.embedding_model,
        "reranker_model": settings.reranker_model,
        "api_key_configured": bool(settings.groq_api_key),
    }


@app.patch("/api/settings")
def update_settings(payload: PreferencesUpdate) -> Dict[str, Any]:
    if payload.theme is not None:
        if payload.theme not in {"Light", "Dark"}:
            raise HTTPException(status_code=422, detail="Theme must be Light or Dark.")
        workspace.set_preference("theme", payload.theme)
    if payload.top_k is not None:
        workspace.set_preference("top_k", payload.top_k)
    if payload.max_iterations is not None:
        workspace.set_preference("max_iterations", payload.max_iterations)
    return get_settings()
