export type Page = "chat" | "documents" | "analytics" | "settings";
export type ChatFilter = "all" | "starred" | "recent" | "trash";

export interface Project {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  chat_count: number;
  is_deleted?: boolean;
}

export interface Citation {
  source: string;
  page: number | null;
  score: number;
  text: string;
}

export interface MessageMetadata {
  confidence?: number;
  citations?: Citation[];
  trace?: Record<string, unknown>;
  feedback?: string;
}

export interface ChatMessage {
  message_id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  metadata: MessageMetadata;
  created_at: string;
}

export interface Chat {
  chat_id: string;
  project_id: string;
  project_name: string;
  title: string;
  is_starred: boolean;
  is_deleted: boolean;
  uses_legacy_index?: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: ChatMessage[];
  documents?: WorkspaceDocument[];
}

export interface WorkspaceDocument {
  document_id: string;
  chat_id: string;
  file_name: string;
  file_type: string;
  file_size: number | null;
  storage_path: string | null;
  processing_status: "Uploaded" | "Processing" | "Indexed" | "Failed" | string;
  uploaded_at: string;
}

export interface Health {
  status: string;
  rag_ready: boolean;
  dependencies: Record<string, boolean>;
  has_groq_key: boolean;
  model: string;
}

export interface Preferences {
  theme: "Light" | "Dark";
  top_k: number;
  max_iterations: number;
  model: string;
  embedding_model: string;
  reranker_model: string;
  api_key_configured: boolean;
}

export interface Analytics {
  counts: {
    projects: number;
    conversations: number;
    messages: number;
    documents: number;
    indexed_documents: number;
  };
  activity: { kind: string; title: string; timestamp: string }[];
  document_types: { type: string; count: number }[];
}
