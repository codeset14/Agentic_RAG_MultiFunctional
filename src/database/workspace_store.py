from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class WorkspaceStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(project_id),
                    title TEXT NOT NULL,
                    is_starred INTEGER NOT NULL DEFAULT 0,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    uses_legacy_index INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_chat_created
                    ON messages(chat_id, created_at);
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    storage_path TEXT,
                    processing_status TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    UNIQUE(chat_id, file_name)
                );
                CREATE INDEX IF NOT EXISTS documents_chat_uploaded
                    ON documents(chat_id, uploaded_at);
                CREATE TABLE IF NOT EXISTS preferences (
                    preference_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            project_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(projects)").fetchall()
            }
            if "is_deleted" not in project_columns:
                connection.execute(
                    "ALTER TABLE projects ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"
                )

    def ensure_default_workspace(self, uses_legacy_index: bool = False) -> str:
        with self._connection() as connection:
            project = connection.execute(
                "SELECT project_id FROM projects WHERE is_deleted = 0 ORDER BY created_at LIMIT 1"
            ).fetchone()
            if project:
                chat = connection.execute(
                    "SELECT chat_id FROM chats WHERE project_id = ? AND is_deleted = 0 "
                    "ORDER BY created_at LIMIT 1",
                    (project["project_id"],),
                ).fetchone()
                if chat:
                    return str(chat["chat_id"])
                return self._insert_chat(
                    connection, str(project["project_id"]), "New Chat"
                )

            project_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO projects(project_id, name, description, created_at) "
                "VALUES (?, ?, ?, ?)",
                (project_id, "My Workspace", "Your private RAG workspace.", _now()),
            )
            return self._insert_chat(
                connection, project_id, "New Chat", uses_legacy_index
            )

    def _insert_chat(
        self,
        connection: sqlite3.Connection,
        project_id: str,
        title: str,
        uses_legacy_index: bool = False,
    ) -> str:
        chat_id = str(uuid.uuid4())
        now = _now()
        connection.execute(
            "INSERT INTO chats(chat_id, project_id, title, uses_legacy_index, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, project_id, title, int(uses_legacy_index), now, now),
        )
        return chat_id

    def create_project(self, name: str, description: str = "") -> str:
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be empty.")
        project_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO projects(project_id, name, description, created_at) "
                "VALUES (?, ?, ?, ?)",
                (project_id, name, description.strip(), _now()),
            )
            self._insert_chat(connection, project_id, "New Chat")
        return project_id

    def list_projects(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT p.project_id, p.name, p.description, p.created_at, p.is_deleted,
                    COUNT(c.chat_id) AS chat_count
                FROM projects p
                LEFT JOIN chats c ON c.project_id = p.project_id AND c.is_deleted = 0
                WHERE (? = 1 OR p.is_deleted = 0)
                GROUP BY p.project_id
                ORDER BY p.created_at
                """,
                (int(include_deleted),),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_project(
        self, project_id: str, name: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        updates = []
        params: List[Any] = []
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Project name cannot be empty.")
            updates.append("name = ?")
            params.append(clean_name)
        if description is not None:
            updates.append("description = ?")
            params.append(description.strip())
        if not updates:
            return
        params.append(project_id)
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE project_id = ? AND is_deleted = 0",
                params,
            )
            if cursor.rowcount == 0:
                raise ValueError("Project does not exist.")

    def set_project_deleted(self, project_id: str, deleted: bool = True) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE projects SET is_deleted = ? WHERE project_id = ?",
                (int(deleted), project_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Project does not exist.")
            connection.execute(
                "UPDATE chats SET is_deleted = ?, updated_at = ? WHERE project_id = ?",
                (int(deleted), _now(), project_id),
            )

    def create_chat(self, project_id: str, title: str = "New Chat") -> str:
        with self._connection() as connection:
            project = connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ? AND is_deleted = 0", (project_id,)
            ).fetchone()
            if not project:
                raise ValueError("Project does not exist.")
            return self._insert_chat(connection, project_id, title.strip() or "New Chat")

    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT c.*, p.name AS project_name
                FROM chats c JOIN projects p ON p.project_id = c.project_id
                WHERE c.chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_chats(
        self,
        project_id: Optional[str] = None,
        starred: bool = False,
        deleted: bool = False,
        search: str = "",
    ) -> List[Dict[str, Any]]:
        clauses = ["c.is_deleted = ?"]
        params: List[Any] = [int(deleted)]
        if project_id:
            clauses.append("c.project_id = ?")
            params.append(project_id)
        if starred:
            clauses.append("c.is_starred = 1")
        if not deleted:
            clauses.append("p.is_deleted = 0")
        if search.strip():
            clauses.append(
                "(c.title LIKE ? OR p.name LIKE ? OR EXISTS (SELECT 1 FROM messages m "
                "WHERE m.chat_id = c.chat_id AND m.content LIKE ?))"
            )
            term = f"%{search.strip()}%"
            params.extend((term, term, term))
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT c.chat_id, c.project_id, c.title, c.is_starred, c.is_deleted,
                    c.uses_legacy_index, c.created_at, c.updated_at, p.name AS project_name,
                    (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.chat_id) AS message_count
                FROM chats c JOIN projects p ON p.project_id = c.project_id
                WHERE {' AND '.join(clauses)}
                ORDER BY c.updated_at DESC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def rename_chat(self, chat_id: str, title: str) -> None:
        title = title.strip()
        if not title:
            raise ValueError("Chat title cannot be empty.")
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE chat_id = ?",
                (title, _now(), chat_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Chat does not exist.")

    def toggle_star(self, chat_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT is_starred FROM chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if not row:
                raise ValueError("Chat does not exist.")
            value = not bool(row["is_starred"])
            connection.execute(
                "UPDATE chats SET is_starred = ?, updated_at = ? WHERE chat_id = ?",
                (int(value), _now(), chat_id),
            )
        return value

    def duplicate_chat(self, chat_id: str) -> str:
        with self._connection() as connection:
            original = connection.execute(
                "SELECT project_id, title FROM chats WHERE chat_id = ? AND is_deleted = 0",
                (chat_id,),
            ).fetchone()
            if not original:
                raise ValueError("Chat does not exist.")
            duplicate_id = self._insert_chat(
                connection,
                str(original["project_id"]),
                f"Copy of {original['title']}",
            )
            messages = connection.execute(
                "SELECT role, content, metadata, created_at FROM messages "
                "WHERE chat_id = ? ORDER BY created_at",
                (chat_id,),
            ).fetchall()
            for message in messages:
                connection.execute(
                    "INSERT INTO messages(message_id, chat_id, role, content, metadata, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        duplicate_id,
                        message["role"],
                        message["content"],
                        message["metadata"],
                        message["created_at"],
                    ),
                )
        return duplicate_id

    def set_chat_deleted(self, chat_id: str, deleted: bool = True) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE chats SET is_deleted = ?, updated_at = ? WHERE chat_id = ?",
                (int(deleted), _now(), chat_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Chat does not exist.")

    def move_chat(self, chat_id: str, project_id: str) -> None:
        with self._connection() as connection:
            project = connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ? AND is_deleted = 0",
                (project_id,),
            ).fetchone()
            if not project:
                raise ValueError("Destination project does not exist.")
            cursor = connection.execute(
                "UPDATE chats SET project_id = ?, updated_at = ? WHERE chat_id = ?",
                (project_id, _now(), chat_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Chat does not exist.")

    def add_message(
        self, chat_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        if role not in {"user", "assistant"}:
            raise ValueError("Message role must be user or assistant.")
        message_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO messages(message_id, chat_id, role, content, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    chat_id,
                    role,
                    content,
                    json.dumps(metadata or {}, ensure_ascii=False, default=_json_default),
                    _now(),
                ),
            )
            connection.execute(
                "UPDATE chats SET updated_at = ? WHERE chat_id = ?", (_now(), chat_id)
            )
        return message_id

    def list_messages(self, chat_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT message_id, chat_id, role, content, metadata, created_at "
                "FROM messages WHERE chat_id = ? ORDER BY created_at, rowid",
                (chat_id,),
            ).fetchall()
        messages = [dict(row) for row in rows]
        for message in messages:
            message["metadata"] = json.loads(message["metadata"])
        return messages

    def clear_messages(self, chat_id: str) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            connection.execute(
                "UPDATE chats SET updated_at = ? WHERE chat_id = ?", (_now(), chat_id)
            )

    def set_message_feedback(self, message_id: str, feedback: str) -> None:
        if feedback not in {"up", "down"}:
            raise ValueError("Feedback must be up or down.")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT metadata FROM messages WHERE message_id = ? AND role = 'assistant'",
                (message_id,),
            ).fetchone()
            if not row:
                raise ValueError("Assistant message does not exist.")
            metadata = json.loads(row["metadata"])
            metadata["feedback"] = feedback
            connection.execute(
                "UPDATE messages SET metadata = ? WHERE message_id = ?",
                (json.dumps(metadata, ensure_ascii=False), message_id),
            )

    def add_document(
        self,
        chat_id: str,
        file_name: str,
        file_type: str,
        file_size: Optional[int],
        storage_path: Optional[str],
        status: str,
    ) -> str:
        document_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO documents(document_id, chat_id, file_name, file_type, file_size, "
                "storage_path, processing_status, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document_id, chat_id, file_name, file_type, file_size,
                    storage_path, status, _now(),
                ),
            )
        return document_id

    def list_documents(self, chat_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM documents WHERE chat_id = ? ORDER BY uploaded_at DESC",
                (chat_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_document_status(self, document_id: str, status: str) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE documents SET processing_status = ? WHERE document_id = ?",
                (status, document_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Document does not exist.")

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not row:
                raise ValueError("Document does not exist.")
            connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        return dict(row)

    def get_preference(self, key: str, default: Any) -> Any:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM preferences WHERE preference_key = ?", (key,)
            ).fetchone()
        if not row:
            return default
        return json.loads(row["value"])

    def set_preference(self, key: str, value: Any) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO preferences(preference_key, value) VALUES (?, ?) "
                "ON CONFLICT(preference_key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value)),
            )

    def analytics(self) -> Dict[str, Any]:
        with self._connection() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM projects WHERE is_deleted = 0) AS projects,
                    (SELECT COUNT(*) FROM chats WHERE is_deleted = 0) AS conversations,
                    (SELECT COUNT(*) FROM messages m JOIN chats c ON c.chat_id = m.chat_id
                        WHERE c.is_deleted = 0) AS messages,
                    (SELECT COUNT(*) FROM documents d JOIN chats c ON c.chat_id = d.chat_id
                        WHERE c.is_deleted = 0) AS documents,
                    (SELECT COUNT(*) FROM documents d JOIN chats c ON c.chat_id = d.chat_id
                        WHERE c.is_deleted = 0 AND d.processing_status = 'Indexed') AS indexed_documents
                """
            ).fetchone()
            activity = connection.execute(
                """
                SELECT 'Message' AS kind, c.title AS title, m.created_at AS timestamp
                FROM messages m JOIN chats c ON c.chat_id = m.chat_id
                WHERE c.is_deleted = 0
                UNION ALL
                SELECT 'Document', d.file_name, d.uploaded_at
                FROM documents d JOIN chats c ON c.chat_id = d.chat_id
                WHERE c.is_deleted = 0
                ORDER BY timestamp DESC LIMIT 10
                """
            ).fetchall()
        return {
            "counts": dict(counts),
            "activity": [dict(row) for row in activity],
        }
