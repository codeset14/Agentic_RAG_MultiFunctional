import { useState } from "react";
import {
  CheckCircle2,
  Clock3,
  Eye,
  FileArchive,
  FileSpreadsheet,
  FileText,
  LoaderCircle,
  MoreVertical,
  Paperclip,
  Trash2,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getErrorMessage, workspaceApi } from "../lib/api";
import type { Chat, WorkspaceDocument } from "../types";

function bytesLabel(bytes: number | null) {
  if (bytes === null) return "Size unavailable";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fileIcon(type: string) {
  if (type === "CSV" || type === "XLSX") return FileSpreadsheet;
  if (type === "ZIP" || type === "PPTX") return FileArchive;
  return FileText;
}

function StatusMark({ status }: { status: string }) {
  if (status === "Indexed") return <CheckCircle2 size={14} className="status-indexed" />;
  if (status === "Failed") return <XCircle size={14} className="status-failed" />;
  if (status === "Processing") return <LoaderCircle size={14} className="status-processing spin" />;
  return <Clock3 size={14} className="status-uploaded" />;
}

export function DocumentsPanel({
  chat,
  compact = false,
}: {
  chat: Chat | undefined;
  compact?: boolean;
}) {
  const queryClient = useQueryClient();
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const chatId = chat?.chat_id;
  const documentsQuery = useQuery({
    queryKey: ["documents", chatId],
    queryFn: () => workspaceApi.documents(chatId!),
    enabled: Boolean(chatId),
  });
  const documents = documentsQuery.data ?? [];
  const upload = useMutation({
    mutationFn: (files: File[]) => workspaceApi.uploadDocuments(chatId!, files),
    onSuccess: async () => {
      setError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["documents", chatId] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const remove = useMutation({
    mutationFn: (id: string) => workspaceApi.deleteDocument(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["documents", chatId] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const onDrop = (files: File[]) => {
    if (files.length && chatId) upload.mutate(files);
  };
  const dropzone = useDropzone({
    onDrop,
    disabled: !chatId || upload.isPending,
    multiple: true,
    accept: {
      "application/pdf": [".pdf"],
      "text/plain": [".txt"],
      "text/csv": [".csv"],
      "application/vnd.ms-excel": [".csv"],
    },
  });

  return (
    <section className={`documents-panel ${compact ? "documents-panel-compact" : ""}`}>
      {!compact && (
        <div className="section-title-row">
          <div><h2>Documents</h2><p>Only files attached to this chat are shown.</p></div>
          <span className="count-badge">{documents.length}</span>
        </div>
      )}
      {!compact && (
        <div
          {...dropzone.getRootProps()}
          className={`upload-dropzone ${dropzone.isDragActive ? "dropzone-active" : ""}`}
        >
          <input {...dropzone.getInputProps()} />
          <div className="dropzone-icon"><UploadCloud size={20} /></div>
          <div>
            <strong>{upload.isPending ? "Uploading and indexing…" : "Drop files to add them"}</strong>
            <span>or <button type="button" onClick={dropzone.open}>browse files</button></span>
            <small>PDF, TXT, CSV · Up to 200 MB each</small>
          </div>
        </div>
      )}
      {upload.isPending && (
        <div className="upload-progress"><LoaderCircle size={15} className="spin" /> Indexing into this chat’s private search index…</div>
      )}
      {error && <div className="inline-error"><span>{error}</span><button onClick={() => setError("")}><X size={14} /></button></div>}
      {documentsQuery.isLoading && <div className="loading-inline">Loading documents…</div>}
      {documentsQuery.isError && <div className="inline-error">{getErrorMessage(documentsQuery.error)}</div>}
      {!documentsQuery.isLoading && documents.length === 0 && (
        <div className="empty-documents"><Paperclip size={18} /><span>No documents in this conversation yet.</span></div>
      )}
      <div className="document-list">
        {documents.map((document) => (
          <DocumentRow
            key={document.document_id}
            document={document}
            onPreview={() => setPreviewId(document.document_id)}
            onDelete={() => remove.mutate(document.document_id)}
            deleting={remove.isPending && remove.variables === document.document_id}
          />
        ))}
      </div>
      <DocumentPreview documentId={previewId} onClose={() => setPreviewId(null)} />
    </section>
  );
}

function DocumentRow({
  document,
  onPreview,
  onDelete,
  deleting,
}: {
  document: WorkspaceDocument;
  onPreview: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  const Icon = fileIcon(document.file_type);
  return (
    <article className="document-row">
      <div className={`file-icon file-icon-${document.file_type.toLowerCase()}`}><Icon size={17} /></div>
      <div className="document-main">
        <strong title={document.file_name}>{document.file_name}</strong>
        <span>{bytesLabel(document.file_size)} <i /> {new Date(document.uploaded_at).toLocaleDateString()}</span>
        <span className={`document-status status-text-${document.processing_status.toLowerCase()}`}>
          <StatusMark status={document.processing_status} /> {document.processing_status}
        </span>
      </div>
      <details className="row-menu-wrap document-menu-wrap">
        <summary className="icon-button row-menu-trigger" aria-label="Document actions">
          {deleting ? <LoaderCircle size={15} className="spin" /> : <MoreVertical size={16} />}
        </summary>
        <div className="row-menu">
          <button onClick={onPreview}><Eye size={15} /> Preview</button>
          <button className="menu-danger" onClick={onDelete} disabled={deleting}><Trash2 size={15} /> Delete</button>
        </div>
      </details>
    </article>
  );
}

function DocumentPreview({
  documentId,
  onClose,
}: {
  documentId: string | null;
  onClose: () => void;
}) {
  const preview = useQuery({
    queryKey: ["document-preview", documentId],
    queryFn: () => workspaceApi.previewDocument(documentId!),
    enabled: Boolean(documentId),
    retry: false,
  });

  return (
    <Dialog.Root open={Boolean(documentId)} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content preview-dialog">
          <div className="dialog-header">
            <div><Dialog.Title>{preview.data?.file_name || "Document preview"}</Dialog.Title><Dialog.Description>Text extracted from this chat’s document.</Dialog.Description></div>
            <Dialog.Close className="icon-button"><X size={18} /></Dialog.Close>
          </div>
          {preview.isLoading && <div className="loading-inline">Extracting document text…</div>}
          {preview.isError && <div className="inline-error">{getErrorMessage(preview.error)}</div>}
          {preview.data && <pre className="preview-text">{preview.data.text || "No selectable text was found in this file."}</pre>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
