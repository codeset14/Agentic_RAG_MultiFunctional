import { useMemo, useState } from "react";
import {
  Archive,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  FileText,
  FolderPlus,
  MessageCircle,
  MoreHorizontal,
  Plus,
  Search,
  Settings2,
  Star,
  Trash2,
  Undo2,
  X,
  Sparkles,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getErrorMessage, workspaceApi } from "../lib/api";
import { useWorkspace } from "../store/useWorkspace";
import type { Chat, Project } from "../types";

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

function timeAgo(value: string) {
  const minutes = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 60_000),
  );
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ChatRow({
  chat,
  selected,
  onSelect,
  onError,
}: {
  chat: Chat;
  selected: boolean;
  onSelect: () => void;
  onError: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const updateChat = useMutation({
    mutationFn: (patch: { title?: string; is_starred?: boolean; is_deleted?: boolean }) =>
      workspaceApi.updateChat(chat.chat_id, patch),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      await queryClient.invalidateQueries({ queryKey: ["chat", chat.chat_id] });
    },
    onError: (error) => onError(getErrorMessage(error)),
  });
  const duplicate = useMutation({
    mutationFn: () => workspaceApi.duplicateChat(chat.chat_id),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      useWorkspace.getState().setActiveChat(created.chat_id, created.project_id);
    },
    onError: (error) => onError(getErrorMessage(error)),
  });

  const rename = () => {
    const title = window.prompt("Rename conversation", chat.title);
    if (title?.trim()) updateChat.mutate({ title: title.trim() });
  };

  return (
    <div className={`chat-row ${selected ? "chat-row-active" : ""}`}>
      <button className="chat-row-main" onClick={onSelect} title={chat.title}>
        <MessageCircle size={15} strokeWidth={1.8} />
        <span className="chat-row-title">{chat.title}</span>
        <span className="chat-row-time">{timeAgo(chat.updated_at)}</span>
      </button>
      <details className="row-menu-wrap">
        <summary className="icon-button row-menu-trigger" aria-label="Conversation actions">
          <MoreHorizontal size={16} />
        </summary>
        <div className="row-menu">
          {chat.is_deleted ? (
            <button onClick={() => updateChat.mutate({ is_deleted: false })}>
              <Undo2 size={15} /> Restore
            </button>
          ) : (
            <>
              <button onClick={rename}><FileText size={15} /> Rename</button>
              <button onClick={() => updateChat.mutate({ is_starred: !chat.is_starred })}>
                <Star size={15} /> {chat.is_starred ? "Unstar" : "Add to starred"}
              </button>
              <button onClick={() => duplicate.mutate()}>
                <Archive size={15} /> Duplicate
              </button>
              <button className="menu-danger" onClick={() => updateChat.mutate({ is_deleted: true })}>
                <Trash2 size={15} /> Move to trash
              </button>
            </>
          )}
        </div>
      </details>
    </div>
  );
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const queryClient = useQueryClient();
  const {
    activeChatId,
    activeProjectId,
    sidebarCollapsed,
    filter,
    search,
    setActiveChat,
    setFilter,
    setPage,
    setSearch,
    toggleSidebar,
  } = useWorkspace();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [error, setError] = useState("");
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: workspaceApi.projects,
  });
  const deletedProjectsQuery = useQuery({
    queryKey: ["deleted-projects"],
    queryFn: workspaceApi.deletedProjects,
    enabled: filter === "trash",
  });
  const chatsQuery = useQuery({
    queryKey: ["chats", filter, search],
    queryFn: () =>
      workspaceApi.chats({
        starred: filter === "starred",
        deleted: filter === "trash",
        search,
      }),
    placeholderData: (previous) => previous,
  });
  const projects =
    filter === "trash"
      ? [...(projectsQuery.data ?? []), ...(deletedProjectsQuery.data ?? [])]
      : projectsQuery.data ?? [];
  const chats = chatsQuery.data ?? [];
  const createProject = useMutation({
    mutationFn: () => workspaceApi.createProject(projectName.trim(), projectDescription.trim()),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      setActiveChat(
        (await workspaceApi.chats({ project_id: project.project_id }))[0]?.chat_id ?? "",
        project.project_id,
      );
      setProjectName("");
      setProjectDescription("");
      setDialogOpen(false);
      setPage("chat");
      setError("");
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });
  const createChat = useMutation({
    mutationFn: (projectId: string) => workspaceApi.createChat(projectId),
    onSuccess: async (chat) => {
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      setActiveChat(chat.chat_id, chat.project_id);
      setPage("chat");
      onCloseMobile();
    },
    onError: (cause) => setError(getErrorMessage(cause)),
  });

  const groupedChats = useMemo(
    () =>
      projects
        .map((project) => ({
          project,
          chats: chats.filter((chat) => chat.project_id === project.project_id),
        }))
        .filter((group) => group.chats.length > 0),
    [projects, chats],
  );

  if (sidebarCollapsed && !mobileOpen) {
    return (
      <aside className="sidebar sidebar-compact">
        <button className="brand-symbol" onClick={toggleSidebar} title="Expand navigation">
          <Sparkles size={24} />
        </button>
        <button className="icon-button compact-toggle" onClick={toggleSidebar} aria-label="Expand sidebar">
          <ChevronRight size={17} />
        </button>
      </aside>
    );
  }

  return (
    <>
      {mobileOpen && <button className="mobile-backdrop" onClick={onCloseMobile} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? "sidebar-mobile-open" : ""}`}>
        <div className="brand-lockup">
          <div className="brand-symbol"><Sparkles size={25} fill="currentColor" /></div>
          <div className="brand-copy">
            <strong>Agentic RAG</strong>
            <span>Smarter Search. Deeper Insights.</span>
          </div>
          <button className="icon-button sidebar-collapse" onClick={toggleSidebar} aria-label="Collapse sidebar">
            <ChevronLeft size={17} />
          </button>
          <button className="icon-button mobile-close" onClick={onCloseMobile} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <div className="sidebar-actions">
          <button className="button button-primary new-project-button" onClick={() => setDialogOpen(true)}>
            <FolderPlus size={16} /> New Project
          </button>
          <button
            className="button button-secondary new-chat-button"
            disabled={!projects.length || createChat.isPending}
            onClick={() => {
              const projectId =
                activeProjectId && projects.some((item) => item.project_id === activeProjectId)
                  ? activeProjectId
                  : projects[0]?.project_id;
              if (projectId) createChat.mutate(projectId);
            }}
          >
            <Plus size={16} /> New Chat
          </button>
        </div>

        <label className="sidebar-search">
          <Search size={16} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search projects and chats"
          />
          {search && (
            <button className="search-clear" onClick={() => setSearch("")} aria-label="Clear search">
              <X size={14} />
            </button>
          )}
        </label>

        <nav className="sidebar-filters" aria-label="Chat filters">
          <button className={filter === "all" ? "filter-active" : ""} onClick={() => setFilter("all")}>
            <MessageCircle size={15} /> All chats
          </button>
          <button className={filter === "recent" ? "filter-active" : ""} onClick={() => setFilter("recent")}>
            <Clock3 size={15} /> Recent
          </button>
          <button className={filter === "starred" ? "filter-active" : ""} onClick={() => setFilter("starred")}>
            <Star size={15} /> Starred
          </button>
          <button className={filter === "trash" ? "filter-active" : ""} onClick={() => setFilter("trash")}>
            <Trash2 size={15} /> Trash
          </button>
        </nav>

        <div className="sidebar-section-heading">
          <span>{filter === "trash" ? "Recently deleted" : "Your projects"}</span>
          <button className="icon-button small-icon" onClick={() => setDialogOpen(true)} title="Add project">
            <Plus size={15} />
          </button>
        </div>

        <div className="project-list">
          {projectsQuery.isLoading && <div className="loading-inline">Loading workspace…</div>}
          {projectsQuery.isError && <div className="inline-error">{getErrorMessage(projectsQuery.error)}</div>}
          {groupedChats.map(({ project, chats: projectChats }) => (
            <ProjectGroup
              key={project.project_id}
              project={project}
              chats={filter === "recent" ? projectChats.slice(0, 5) : projectChats}
              activeChatId={activeChatId}
              onSelect={(chat) => {
                setActiveChat(chat.chat_id, chat.project_id);
                setPage("chat");
                onCloseMobile();
              }}
              onError={setError}
              onCreateChat={() => createChat.mutate(project.project_id)}
              trash={filter === "trash"}
              onRestoreProject={() => {
                workspaceApi.restoreProject(project.project_id).then(async () => {
                  await queryClient.invalidateQueries({ queryKey: ["projects"] });
                  await queryClient.invalidateQueries({ queryKey: ["deleted-projects"] });
                  await queryClient.invalidateQueries({ queryKey: ["chats"] });
                }).catch((cause) => setError(getErrorMessage(cause)));
              }}
            />
          ))}
          {!projectsQuery.isLoading && !deletedProjectsQuery.isLoading && groupedChats.length === 0 && (
            <div className="empty-sidebar">
              {filter === "trash" ? "Trash is empty." : search ? "No matching conversations." : "Create a project to get started."}
            </div>
          )}
        </div>

        {error && (
          <div className="sidebar-error" role="alert">
            <span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={14} /></button>
          </div>
        )}

        <div className="sidebar-bottom">
          <button className="upgrade-card" onClick={() => setError("Plans are not configured for this local workspace.")}>
            <span className="upgrade-title"><Sparkles size={15} /> Personal workspace</span>
            <span>Projects and documents stay on this device.</span>
          </button>
          <div className="profile-row">
            <div className="profile-avatar">A</div>
            <div className="profile-copy"><strong>Local workspace</strong><span>Private · on this device</span></div>
            <button className="icon-button small-icon" onClick={() => setPage("settings")} title="Settings">
              <Settings2 size={16} />
            </button>
          </div>
        </div>
      </aside>

      <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <div className="dialog-header">
              <div><Dialog.Title>New project</Dialog.Title><Dialog.Description>Organize conversations and their documents in a workspace.</Dialog.Description></div>
              <Dialog.Close className="icon-button"><X size={18} /></Dialog.Close>
            </div>
            <form
              className="dialog-form"
              onSubmit={(event) => {
                event.preventDefault();
                if (projectName.trim()) createProject.mutate();
              }}
            >
              <label>Project name<input autoFocus maxLength={80} value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="e.g. Research notes" required /></label>
              <label>Description <span className="muted-small">Optional</span><textarea maxLength={500} rows={3} value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} placeholder="What are you working on?" /></label>
              {error && <div className="inline-error">{error}</div>}
              <div className="dialog-actions">
                <Dialog.Close className="button button-secondary">Cancel</Dialog.Close>
                <button className="button button-primary" disabled={createProject.isPending || !projectName.trim()}>
                  {createProject.isPending ? "Creating…" : "Create project"}
                </button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}

function ProjectGroup({
  project,
  chats,
  activeChatId,
  onSelect,
  onError,
  onCreateChat,
  trash,
  onRestoreProject,
}: {
  project: Project;
  chats: Chat[];
  activeChatId: string | null;
  onSelect: (chat: Chat) => void;
  onError: (message: string) => void;
  onCreateChat: () => void;
  trash: boolean;
  onRestoreProject: () => void;
}) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(true);
  const updateProject = useMutation({
    mutationFn: (patch: { name?: string; description?: string }) =>
      workspaceApi.updateProject(project.project_id, patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
    onError: (error) => onError(getErrorMessage(error)),
  });
  const removeProject = useMutation({
    mutationFn: () => workspaceApi.deleteProject(project.project_id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
    onError: (error) => onError(getErrorMessage(error)),
  });
  const renameProject = () => {
    const name = window.prompt("Rename project", project.name);
    if (name?.trim()) updateProject.mutate({ name: name.trim() });
  };
  const deleteProject = () => {
    if (window.confirm(`Move “${project.name}” and its conversations to Trash?`)) {
      removeProject.mutate();
    }
  };
  const chatsToShow = trash ? chats : chats;

  return (
    <section className="project-group">
      <div className="project-heading">
        <button className="project-expander" onClick={() => setExpanded(!expanded)}>
          <span className="project-icon"><FileText size={15} /></span>
          <span className="project-name">{project.name}</span>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        {!trash && !project.is_deleted && (
          <details className="row-menu-wrap">
            <summary className="icon-button row-menu-trigger" aria-label={`Actions for ${project.name}`}><MoreHorizontal size={16} /></summary>
            <div className="row-menu">
              <button onClick={onCreateChat}><Plus size={15} /> New chat</button>
              <button onClick={renameProject}><FileText size={15} /> Rename project</button>
              <button className="menu-danger" onClick={deleteProject}><Trash2 size={15} /> Move to trash</button>
            </div>
          </details>
        )}
        {project.is_deleted && (
          <button className="restore-project-button" onClick={onRestoreProject}>
            <Undo2 size={14} /> Restore
          </button>
        )}
      </div>
      {expanded && (
        <div className="project-chats">
          {(project.is_deleted ? [] : chatsToShow).map((chat) => (
            <ChatRow
              key={chat.chat_id}
              chat={chat}
              selected={chat.chat_id === activeChatId}
              onSelect={() => onSelect(chat)}
              onError={onError}
            />
          ))}
          {!trash && (
            <button className="add-chat-inline" onClick={onCreateChat}>
              <Plus size={14} /> Add conversation
            </button>
          )}
        </div>
      )}
    </section>
  );
}
