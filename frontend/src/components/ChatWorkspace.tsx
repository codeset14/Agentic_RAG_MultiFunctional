import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronDown,
  Copy,
  FileText,
  Lightbulb,
  LoaderCircle,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  WandSparkles,
  X,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { getErrorMessage, workspaceApi } from "../lib/api";
import { useWorkspace } from "../store/useWorkspace";
import type { Chat, ChatMessage, Health } from "../types";

const quickPrompts = [
  { label: "Research documents", icon: Search, prompt: "Find the most relevant information in this chat's documents." },
  { label: "Explain a concept", icon: Lightbulb, prompt: "Explain the key concepts in my documents clearly and with examples." },
  { label: "Generate Python code", icon: WandSparkles, prompt: "Write Python code based on the documents in this chat. Explain the approach." },
  { label: "Analyze data", icon: ArrowDownToLine, prompt: "Analyze the data in this chat's documents and summarize evidence-based findings." },
];

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const language = /language-(\w+)/.exec(className || "")?.[1];
            const text = String(children).replace(/\n$/, "");
            if (!language && !text.includes("\n")) {
              return <code className="inline-code" {...props}>{children}</code>;
            }
            return (
              <SyntaxHighlighter
                style={oneDark}
                language={language || "text"}
                PreTag="div"
                customStyle={{ borderRadius: 12, margin: "12px 0", fontSize: 12 }}
              >
                {text}
              </SyntaxHighlighter>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function MessageBubble({
  message,
  chatId,
  onRegenerate,
  isLastAssistant,
}: {
  message: ChatMessage;
  chatId: string;
  onRegenerate: () => void;
  isLastAssistant: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const queryClient = useQueryClient();
  const feedback = useMutation({
    mutationFn: (value: "up" | "down") => workspaceApi.submitFeedback(message.message_id, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["messages", chatId] }),
  });
  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  const isAssistant = message.role === "assistant";

  return (
    <article className={`message-line ${isAssistant ? "message-assistant" : "message-user"}`}>
      {isAssistant && <div className="assistant-avatar"><Sparkles size={17} fill="currentColor" /></div>}
      <div className="message-content-wrap">
        <div className="message-meta">
          <strong>{isAssistant ? "Agentic RAG" : "You"}</strong>
          <span>{formatTime(message.created_at)}</span>
        </div>
        <div className={`message-bubble ${isAssistant ? "assistant-bubble" : "user-bubble"}`}>
          <MarkdownContent content={message.content} />
          {isAssistant && message.metadata.confidence !== undefined && (
            <div className="confidence-line">
              <span>Evidence confidence</span>
              <div className="confidence-track"><span style={{ width: `${Math.min(100, Math.max(0, message.metadata.confidence * 100))}%` }} /></div>
              <b>{Math.round(message.metadata.confidence * 100)}%</b>
            </div>
          )}
          {isAssistant && Boolean(message.metadata.citations?.length) && (
            <details className="sources-disclosure">
              <summary><FileText size={14} /> Sources ({message.metadata.citations?.length}) <ChevronDown size={14} /></summary>
              <div className="source-list">
                {message.metadata.citations?.map((citation, index) => (
                  <div className="source-item" key={`${citation.source}-${citation.page}-${index}`}>
                    <div><FileText size={14} /><b>{citation.source}</b>{citation.page && <span>Page {citation.page}</span>}</div>
                    <p>{citation.text}</p>
                  </div>
                ))}
              </div>
            </details>
          )}
          {isAssistant && message.metadata.trace && (
            <details className="trace-disclosure">
              <summary>View agent trace <ChevronDown size={13} /></summary>
              <pre>{JSON.stringify(message.metadata.trace, null, 2)}</pre>
            </details>
          )}
        </div>
        {isAssistant && (
          <div className="message-actions">
            <button className="icon-button" onClick={copy} title="Copy response">{copied ? <Check size={15} /> : <Copy size={15} />}</button>
            <button className={`icon-button ${message.metadata.feedback === "up" ? "feedback-active" : ""}`} onClick={() => feedback.mutate("up")} title="Helpful"><ThumbsUp size={15} /></button>
            <button className={`icon-button ${message.metadata.feedback === "down" ? "feedback-active" : ""}`} onClick={() => feedback.mutate("down")} title="Not helpful"><ThumbsDown size={15} /></button>
            {isLastAssistant && <button className="icon-button" onClick={onRegenerate} title="Regenerate"><RefreshCw size={15} /></button>}
          </div>
        )}
      </div>
      {!isAssistant && <div className="user-avatar">U</div>}
    </article>
  );
}

export function ChatWorkspace({
  chat,
  health,
}: {
  chat: Chat | undefined;
  health: Health | undefined;
}) {
  const queryClient = useQueryClient();
  const { activeChatId, queuedPrompt, clearQueuedPrompt } = useWorkspace();
  const [draft, setDraft] = useState("");
  const [selectedDocument, setSelectedDocument] = useState("");
  const [showTools, setShowTools] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const documentsQuery = useQuery({
    queryKey: ["documents", activeChatId],
    queryFn: () => workspaceApi.documents(activeChatId!),
    enabled: Boolean(activeChatId),
  });
  const messagesQuery = useQuery({
    queryKey: ["messages", activeChatId],
    queryFn: () => workspaceApi.messages(activeChatId!),
    enabled: Boolean(activeChatId),
  });
  const send = useMutation({
    mutationFn: (content: string) => workspaceApi.sendMessage(activeChatId!, content),
    onMutate: () => setError(""),
    onSuccess: async () => {
      setDraft("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["messages", activeChatId] }),
        queryClient.invalidateQueries({ queryKey: ["chats"] }),
        queryClient.invalidateQueries({ queryKey: ["chat", activeChatId] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const upload = useMutation({
    mutationFn: (files: File[]) => workspaceApi.uploadDocuments(activeChatId!, files),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents", activeChatId] });
      await queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const messages = messagesQuery.data ?? [];
  const documents = documentsQuery.data ?? [];

  useEffect(() => {
    if (queuedPrompt) {
      setDraft(queuedPrompt);
      clearQueuedPrompt();
    }
  }, [queuedPrompt, clearQueuedPrompt]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, send.isPending]);

  const submit = (value = draft) => {
    if (!activeChatId || !value.trim() || send.isPending) return;
    const prompt = selectedDocument ? `@${selectedDocument}\n${value.trim()}` : value.trim();
    send.mutate(prompt);
    setDraft("");
  };
  const regenerate = () => {
    const previousPrompt = [...messages].reverse().find((item) => item.role === "user");
    if (previousPrompt) send.mutate(previousPrompt.content);
  };
  const downloadChat = () => {
    const contents = messages.map((message) => `${message.role.toUpperCase()}\n${message.content}`).join("\n\n---\n\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([contents], { type: "text/markdown" }));
    link.download = `${chat?.title || "agentic-rag-chat"}.md`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  if (!chat) {
    return (
      <div className="chat-empty-state">
        <div className="empty-robot"><Sparkles size={34} /></div>
        <h1>Welcome to Agentic RAG</h1>
        <p>Your intelligent workspace for studying, coding, research, and productivity.</p>
        <span>Select or create a conversation to get started.</span>
      </div>
    );
  }

  return (
    <section className="chat-workspace">
      <header className="chat-header">
        <div className="chat-heading">
          <span>{chat.project_name}</span>
          <ArrowRight size={14} />
          <h1>{chat.title}</h1>
        </div>
        <div className="chat-header-actions">
          <span className={`model-chip ${health?.rag_ready ? "model-ready" : "model-unavailable"}`}>
            <span className="status-dot" />{health?.model || "RAG model"}{health?.rag_ready ? "" : " · Setup needed"}
          </span>
          <button className="icon-button" onClick={downloadChat} title="Export conversation" disabled={!messages.length}>
            <ArrowDownToLine size={17} />
          </button>
        </div>
      </header>

      <div className="chat-scroll-area">
        {messagesQuery.isLoading && <div className="loading-inline">Loading conversation…</div>}
        {messagesQuery.isError && <div className="inline-error">{getErrorMessage(messagesQuery.error)}</div>}
        {!messagesQuery.isLoading && messages.length === 0 && (
          <div className="welcome-panel">
            <div className="welcome-art" aria-hidden="true">
              <div className="welcome-orbit orbit-one" /><div className="welcome-orbit orbit-two" />
              <div className="welcome-robot">🤖</div><span className="welcome-star star-one">✦</span><span className="welcome-star star-two">✧</span>
            </div>
            <div className="welcome-copy">
              <div className="eyebrow"><Sparkles size={14} /> YOUR AI WORKSPACE</div>
              <h2>Welcome to Agentic RAG!</h2>
              <p>Ask anything, explore your documents, and let the agent handle the rest.</p>
            </div>
            <div className="quick-prompts">
              {quickPrompts.map(({ label, icon: Icon, prompt }) => (
                <button key={label} onClick={() => setDraft(prompt)}><Icon size={16} /><span>{label}</span></button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message, index) => (
          <MessageBubble
            key={message.message_id}
            message={message}
            chatId={chat.chat_id}
            isLastAssistant={message.role === "assistant" && index === messages.length - 1}
            onRegenerate={regenerate}
          />
        ))}
        {send.isPending && (
          <div className="message-line message-assistant">
            <div className="assistant-avatar"><Sparkles size={17} /></div>
            <div className="typing-indicator"><LoaderCircle size={16} className="spin" /> Searching evidence and preparing a grounded answer…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {error && <div className="chat-error" role="alert"><span>{error}</span><button onClick={() => setError("")}><X size={15} /></button></div>}
      {!health?.rag_ready && (
        <div className="setup-notice">
          <span>RAG backend needs setup before chat or indexing can run.</span>
          <button onClick={() => useWorkspace.getState().setPage("settings")}>View setup <ArrowRight size={14} /></button>
        </div>
      )}
      <div className="composer-wrap">
        <div className="composer">
          <input
            ref={fileRef}
            className="visually-hidden"
            type="file"
            multiple
            accept=".pdf,.txt,.csv"
            onChange={(event) => {
              const selected = Array.from(event.target.files ?? []);
              if (selected.length) upload.mutate(selected);
              event.target.value = "";
            }}
          />
          <button className="icon-button attach-button" onClick={() => fileRef.current?.click()} title="Attach PDF, TXT, or CSV" disabled={upload.isPending}>
            {upload.isPending ? <LoaderCircle size={18} className="spin" /> : <Paperclip size={18} />}
          </button>
          <textarea
            value={draft}
            rows={1}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
              if (event.key === "Escape") setShowTools(false);
            }}
            placeholder="Ask a question… (Shift + Enter for a new line)"
            aria-label="Message"
            disabled={send.isPending}
          />
          <div className="composer-tools">
            <div className="tools-wrap">
              <button className="tools-button" onClick={() => setShowTools(!showTools)}>
                <Sparkles size={15} /> Tools <ChevronDown size={14} />
              </button>
              {showTools && (
                <div className="tools-menu">
                  <div className="tools-menu-heading">Document context</div>
                  <button className={!selectedDocument ? "tool-option-selected" : ""} onClick={() => { setSelectedDocument(""); setShowTools(false); }}>
                    <Search size={15} /> Search all chat documents
                  </button>
                  {documents.map((document) => (
                    <button className={selectedDocument === document.file_name ? "tool-option-selected" : ""} key={document.document_id} onClick={() => { setSelectedDocument(document.file_name); setShowTools(false); }}>
                      <FileText size={15} /> <span>{document.file_name}</span>
                    </button>
                  ))}
                  {!documents.length && <span className="tools-empty">Upload a file to choose its context.</span>}
                  <div className="tool-unavailable">Web search is not configured</div>
                </div>
              )}
            </div>
            <button className="send-button" onClick={() => submit()} disabled={!draft.trim() || send.isPending || !health?.rag_ready} aria-label="Send message">
              {send.isPending ? <LoaderCircle size={18} className="spin" /> : <Send size={17} />}
            </button>
          </div>
        </div>
        {selectedDocument && <div className="selected-document"><FileText size={13} /> Context: {selectedDocument}<button onClick={() => setSelectedDocument("")} aria-label="Clear selected document"><X size={13} /></button></div>}
        <p className="composer-footnote">AI-generated responses can be inaccurate. Verify important information with cited sources.</p>
      </div>
    </section>
  );
}
