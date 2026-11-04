import { useMemo, useState } from "react";
import { FileSearch, FolderOpen, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getErrorMessage, workspaceApi } from "../lib/api";
import { useWorkspace } from "../store/useWorkspace";
import type { Chat } from "../types";
import { DocumentsPanel } from "../components/DocumentsPanel";

export function DocumentsPage({ chat }: { chat: Chat | undefined }) {
  const [search, setSearch] = useState("");
  const [type, setType] = useState("All types");
  const chatId = useWorkspace((state) => state.activeChatId);
  const documents = useQuery({
    queryKey: ["documents", chatId],
    queryFn: () => workspaceApi.documents(chatId!),
    enabled: Boolean(chatId),
  });
  const types = useMemo(
    () => [...new Set((documents.data ?? []).map((document) => document.file_type))].sort(),
    [documents.data],
  );
  const filtered = (documents.data ?? []).filter((document) =>
    (type === "All types" || document.file_type === type) &&
    document.file_name.toLowerCase().includes(search.toLowerCase()),
  );

  if (!chat) {
    return <EmptyDocuments title="Select a conversation" subtitle="Documents are private to each chat." />;
  }

  return (
    <div className="page-scroll documents-page">
      <header className="page-title-block">
        <div className="page-title-icon"><FolderOpen size={19} /></div>
        <div><h1>Documents</h1><p>Manage the files indexed for <b>{chat.title}</b>.</p></div>
        <span className="count-badge page-count">{documents.data?.length ?? 0} files</span>
      </header>
      <DocumentsPanel chat={chat} />
      <section className="document-library">
        <div className="library-toolbar">
          <div className="library-title"><h2>Files in this conversation</h2><span className="count-badge">{filtered.length}</span></div>
          <div className="library-filters">
            <label className="table-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search files" /></label>
            <select value={type} onChange={(event) => setType(event.target.value)} aria-label="Filter by file type">
              <option>All types</option>{types.map((item) => <option key={item}>{item}</option>)}
            </select>
          </div>
        </div>
        {documents.isLoading && <div className="loading-inline">Loading your files…</div>}
        {documents.isError && <div className="inline-error">{getErrorMessage(documents.error)}</div>}
        {!documents.isLoading && !filtered.length && (
          <div className="document-library-empty"><FileSearch size={24} /><strong>No matching files</strong><span>Try a different search or upload a PDF, TXT, or CSV.</span></div>
        )}
        {filtered.length > 0 && (
          <div className="library-list">
            <div className="library-row library-table-header"><span>File</span><span>Type</span><span>Size</span><span>Added</span><span>Status</span><span /></div>
            {filtered.map((document) => (
              <div className="library-row" key={document.document_id}>
                <span className="library-file-name"><i className={`file-type-dot dot-${document.file_type.toLowerCase()}`} />{document.file_name}</span>
                <span>{document.file_type}</span>
                <span>{document.file_size ? `${(document.file_size / 1024).toFixed(1)} KB` : "—"}</span>
                <span>{new Date(document.uploaded_at).toLocaleDateString()}</span>
                <span className={`table-status status-text-${document.processing_status.toLowerCase()}`}>{document.processing_status}</span>
                <span />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function EmptyDocuments({ title, subtitle }: { title: string; subtitle: string }) {
  return <div className="page-empty"><FolderOpen size={30} /><h1>{title}</h1><p>{subtitle}</p></div>;
}
