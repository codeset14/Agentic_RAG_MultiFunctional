# Agentic RAG Workspace

A local project-based RAG workspace with a React, TypeScript, and Vite frontend, a FastAPI API, and the repository's existing Python retrieval pipeline.

## Features

- Persistent projects, conversations, messages, favorites, and trash in SQLite.
- Independent document indexes and conversation histories per chat.
- PDF, TXT, and CSV uploads, previews, indexing state, and removal.
- Existing Groq-powered query analysis, hybrid retrieval, reranking, reasoning, answer validation, and citations.
- Local analytics and saved theme/retrieval preferences.
- Responsive three-panel workspace with light and dark themes.

Web search, account management, sharing, and document formats beyond PDF/TXT/CSV are not configured. The frontend does not simulate these features.

## Requirements

- Python 3.10 or later
- Node.js 20.19+ or 22.12+
- A Groq API key for RAG answers

## Setup

1. Create and activate a Python environment, then install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

   The full requirements include PyTorch, sentence-transformers, and FAISS and may take some time to install. The workspace API and frontend can be run without these model packages, but chat answering and document indexing require them.

2. Create a local `.env` file in the repository root and set `GROQ_API_KEY`. Keep the key private; it is read only by the backend.

3. Install frontend packages:

   ```powershell
   cd frontend
   npm install
   ```

## Run the application

Open two PowerShell terminals from the repository root.

Terminal 1 — FastAPI:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — Vite:

```powershell
cd frontend
npm run dev
```

Open the local address printed by Vite (normally `http://localhost:5173`). The frontend proxies `/api` requests to `http://localhost:8000`. FastAPI health and interactive API documentation are available at `http://localhost:8000/api/health` and `http://localhost:8000/docs`.

The workspace UI and SQLite-backed project/chat operations remain available when RAG model packages or the API key are missing. The health indicator reports whether RAG is ready; chat responses and indexing need the model dependencies and a configured key.

## Data and architecture

- `frontend/` contains the React application and Vite configuration.
- `backend/main.py` exposes workspace and RAG API routes.
- `src/database/workspace_store.py` persists projects, chats, messages, documents, preferences, and feedback.
- Existing ingestion, embedding, retrieval, and agent modules remain under `src/`.
- SQLite data and uploaded files are stored under `data/`; per-chat FAISS indexes are stored under `data/workspaces/<chat_id>/index/`.

If existing `data/index/` FAISS files are found on first launch, the initial chat uses that legacy index. Newly created chats have their own indexes. Duplicating a chat copies its messages but not its documents or index.

## Tests and production build

Run the workspace persistence tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Check the frontend TypeScript types and create a production build:

```powershell
cd frontend
npm run build
```

The API is intended for local use and does not provide user authentication.
