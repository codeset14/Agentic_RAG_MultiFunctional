import { useMemo, useState } from "react";
import {
  BarChart3,
  BookOpenCheck,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Code2,
  FileText,
  Lightbulb,
  MessageSquareText,
  MoreHorizontal,
  Pencil,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getErrorMessage, workspaceApi } from "../lib/api";
import { useWorkspace } from "../store/useWorkspace";
import type { Chat, Project } from "../types";
import { DocumentsPanel } from "./DocumentsPanel";

const tools = [
  { title: "Summarize", caption: "Documents", icon: FileText, prompt: "Summarize the key information in this chat's documents." },
  { title: "Study plan", caption: "From your files", icon: CalendarDays, prompt: "Create a practical study plan based on the documents in this chat." },
  { title: "Write code", caption: "Ask an agent", icon: Code2, prompt: "Write code relevant to the documents in this chat. Explain assumptions." },
  { title: "Analyze data", caption: "Evidence-based", icon: BarChart3, prompt: "Analyze the data in this chat's documents and summarize evidence-based findings." },
];

export function ContextPanel({ chat }: { chat: Chat | undefined }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const { queuePrompt, setPage, setActiveChat } = useWorkspace();
  const analytics = useQuery({
    queryKey: ["analytics"],
    queryFn: workspaceApi.analytics,
  });
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: workspaceApi.projects,
  });
  const projects = projectsQuery.data ?? [];
  const rename = useMutation({
    mutationFn: async () => {
      if (!chat) return;
      const title = window.prompt("Rename conversation", chat.title);
      if (!title?.trim()) return;
      return workspaceApi.updateChat(chat.chat_id, { title: title.trim() });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chats"] }),
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const duplicate = useMutation({
    mutationFn: () => workspaceApi.duplicateChat(chat!.chat_id),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      setActiveChat(created.chat_id, created.project_id);
      setPage("chat");
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const remove = useMutation({
    mutationFn: () => workspaceApi.deleteChat(chat!.chat_id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      const next = await workspaceApi.chats({ project_id: chat!.project_id });
      setActiveChat(next[0]?.chat_id ?? "", chat!.project_id);
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const move = useMutation({
    mutationFn: (projectId: string) => workspaceApi.updateChat(chat!.chat_id, { project_id: projectId }),
    onSuccess: async (updated) => {
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      await queryClient.invalidateQueries({ queryKey: ["chat", chat?.chat_id] });
      setActiveChat(updated.chat_id, updated.project_id);
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const activitySeries = useMemo(() => {
    const activity = analytics.data?.activity ?? [];
    const days = new Map<string, number>();
    activity.forEach((item) => {
      const day = item.timestamp.slice(0, 10);
      days.set(day, (days.get(day) ?? 0) + 1);
    });
    return [...days.values()].slice(0, 8).reverse();
  }, [analytics.data]);

  if (!chat) {
    return (
      <aside className="context-panel">
        <div className="context-empty">
          <div className="context-empty-icon"><ShieldCheck size={19} /></div>
          <strong>Your private workspace</strong>
          <p>Choose a conversation to view its context, documents, and tools.</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="context-panel">
      {error && <div className="inline-error">{error}<button onClick={() => setError("")}>×</button></div>}
      <section className="context-section details-section">
        <div className="context-section-heading">
          <div><MessageSquareText size={16} /><h2>Chat details</h2></div>
          <details className="row-menu-wrap">
            <summary className="icon-button row-menu-trigger" aria-label="Chat details menu"><MoreHorizontal size={17} /></summary>
            <div className="row-menu">
              <button onClick={() => rename.mutate()}><Pencil size={15} /> Rename</button>
              <button onClick={() => duplicate.mutate()}><BookOpenCheck size={15} /> Duplicate</button>
              <button className="menu-danger" onClick={() => {
                if (window.confirm("Move this conversation to Trash?")) remove.mutate();
              }}><Trash2 size={15} /> Move to trash</button>
            </div>
          </details>
        </div>
        <div className="detail-project">
          <div className="project-avatar"><BookOpenCheck size={20} /></div>
          <div className="detail-project-copy"><strong>{chat.project_name}</strong><span>Conversation · {new Date(chat.created_at).toLocaleDateString()}</span></div>
          <span className="active-pill"><i /> Active</span>
        </div>
        <div className="chat-stat-grid">
          <div><MessageSquareText size={15} /><strong>{chat.message_count}</strong><span>Messages</span></div>
          <div><FileText size={15} /><strong>{chat.documents?.length ?? 0}</strong><span>Documents</span></div>
          <div><CalendarDays size={15} /><strong>{new Date(chat.updated_at).toLocaleDateString()}</strong><span>Last active</span></div>
        </div>
        <div className="context-actions">
          <button onClick={() => rename.mutate()}><Pencil size={14} /> Rename</button>
          <button onClick={() => duplicate.mutate()}><BookOpenCheck size={14} /> Duplicate</button>
          <button className="danger-outline" onClick={() => {
            if (window.confirm("Move this conversation to Trash?")) remove.mutate();
          }}><Trash2 size={14} /></button>
        </div>
        <label className="move-chat-select">
          <span>Move to project</span>
          <select
            value={chat.project_id}
            onChange={(event) => move.mutate(event.target.value)}
            aria-label="Move conversation to project"
          >
            {projects.map((project: Project) => <option key={project.project_id} value={project.project_id}>{project.name}</option>)}
          </select>
        </label>
      </section>

      <section className="context-section uploaded-section">
        <div className="context-section-heading">
          <div><FileText size={16} /><h2>Uploaded documents</h2><span className="count-badge">{chat.documents?.length ?? 0}</span></div>
          <button className="text-button" onClick={() => setPage("documents")}>View all <ChevronRight size={14} /></button>
        </div>
        <DocumentsPanel chat={chat} compact />
      </section>

      <section className="context-section quick-tools-section">
        <div className="context-section-heading"><div><Sparkles size={16} /><h2>Quick actions</h2></div></div>
        <div className="quick-tools-grid">
          {tools.map(({ title, caption, icon: Icon, prompt }) => (
            <button key={title} className="quick-tool-card" onClick={() => queuePrompt(prompt)}>
              <span className={`quick-tool-icon quick-tool-${title.toLowerCase().replace(" ", "-")}`}><Icon size={17} /></span>
              <span><strong>{title}</strong><small>{caption}</small></span>
            </button>
          ))}
        </div>
        <button className="quick-tool-card web-unavailable" disabled title="Web search is not configured">
          <span className="quick-tool-icon"><Lightbulb size={17} /></span><span><strong>Search web</strong><small>Not configured</small></span>
        </button>
      </section>

      <section className="context-section project-overview">
        <div className="context-section-heading"><div><BarChart3 size={16} /><h2>Project overview</h2></div><ChevronDown size={14} /></div>
        <p>{projects.find((project) => project.project_id === chat.project_id)?.description || "Your project workspace, powered by Agentic RAG."}</p>
        <div className="project-overview-footer">
          <span>{projects.find((project) => project.project_id === chat.project_id)?.chat_count ?? 0} conversations</span>
          <MiniSparkline values={activitySeries} />
        </div>
      </section>
    </aside>
  );
}

function MiniSparkline({ values }: { values: number[] }) {
  const points = values.length
    ? values.map((value, index) => `${index * (100 / Math.max(1, values.length - 1))},${28 - Math.min(24, value * 5)}`).join(" ")
    : "0,27 20,27 40,27 60,27 80,27 100,27";
  return (
    <svg className="mini-sparkline" viewBox="0 0 100 32" role="img" aria-label="Recent workspace activity">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
