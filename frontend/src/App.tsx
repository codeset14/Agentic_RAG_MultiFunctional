import { useEffect, useState } from "react";
import {
  BarChart3,
  FileText,
  Menu,
  MessageCircle,
  PanelRightClose,
  PanelRightOpen,
  Settings,
  Sparkles,
} from "lucide-react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { ContextPanel } from "./components/ContextPanel";
import { Sidebar } from "./components/Sidebar";
import { getErrorMessage, workspaceApi } from "./lib/api";
import { useWorkspace } from "./store/useWorkspace";
import type { Page } from "./types";

const pageMap: Record<Page, { label: string; icon: typeof MessageCircle; path: string }> = {
  chat: { label: "Chat", icon: MessageCircle, path: "/chat" },
  documents: { label: "Documents", icon: FileText, path: "/documents" },
  analytics: { label: "Analytics", icon: BarChart3, path: "/analytics" },
  settings: { label: "Settings", icon: Settings, path: "/settings" },
};

function Shell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const {
    activeChatId,
    setActiveChat,
    page,
    setPage,
    contextCollapsed,
    toggleContext,
    sidebarCollapsed,
  } = useWorkspace();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: workspaceApi.health,
    retry: 1,
    refetchInterval: 30_000,
  });
  const projects = useQuery({ queryKey: ["projects"], queryFn: workspaceApi.projects });
  const chats = useQuery({ queryKey: ["chats", "all", ""], queryFn: () => workspaceApi.chats() });
  const preferences = useQuery({ queryKey: ["settings"], queryFn: workspaceApi.preferences });
  const chatQuery = useQuery({
    queryKey: ["chat", activeChatId],
    queryFn: () => workspaceApi.chat(activeChatId!),
    enabled: Boolean(activeChatId),
    retry: false,
  });

  useEffect(() => {
    const route = location.pathname.replace("/", "") as Page;
    if (route in pageMap) setPage(route);
    else if (location.pathname === "/") {
      setPage("chat");
      navigate("/chat", { replace: true });
    } else {
      navigate("/chat", { replace: true });
    }
  }, [location.pathname, navigate, setPage]);

  useEffect(() => {
    if (!activeChatId && chats.data?.length) {
      const firstChat = chats.data[0];
      setActiveChat(firstChat.chat_id, firstChat.project_id);
    } else if (activeChatId && chats.data && !chats.data.some((chat) => chat.chat_id === activeChatId)) {
      const firstChat = chats.data[0];
      if (firstChat) setActiveChat(firstChat.chat_id, firstChat.project_id);
    }
  }, [activeChatId, chats.data, setActiveChat]);

  useEffect(() => {
    document.documentElement.dataset.theme = preferences.data?.theme.toLowerCase() ?? "light";
  }, [preferences.data?.theme]);

  const activeChat = chatQuery.data;
  const apiError = health.isError
    ? `API is unavailable: ${getErrorMessage(health.error)}`
    : "";
  return (
    <div className={`app-shell ${sidebarCollapsed ? "app-sidebar-collapsed" : ""} ${contextCollapsed ? "app-context-collapsed" : ""}`}>
      <Sidebar mobileOpen={mobileSidebarOpen} onCloseMobile={() => setMobileSidebarOpen(false)} />
      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-brand">
            <button className="icon-button mobile-menu" onClick={() => setMobileSidebarOpen(true)} aria-label="Open navigation"><Menu size={19} /></button>
            <div className="topbar-logo"><Sparkles size={18} fill="currentColor" /></div>
            <div className="topbar-brand-copy"><strong>Agentic RAG</strong><span>Smarter Search. Deeper Insights.</span></div>
          </div>
          <nav className="top-tabs" aria-label="Main navigation">
            {(Object.keys(pageMap) as Page[]).map((key) => {
              const { label, icon: Icon, path } = pageMap[key];
              return (
                <NavLink
                  key={key}
                  to={path}
                  className={({ isActive }) => `top-tab ${isActive || page === key ? "top-tab-active" : ""}`}
                  onClick={() => setPage(key)}
                >
                  <Icon size={16} /><span>{label}</span>
                  {key === "documents" && activeChat && <small>{activeChat.documents?.length ?? 0}</small>}
                </NavLink>
              );
            })}
          </nav>
          <div className="topbar-right">
            {health.data?.rag_ready ? (
              <span className="connection-pill connection-ready"><i /> RAG ready</span>
            ) : (
              <span className="connection-pill connection-not-ready" title={apiError || "Install backend model dependencies and configure GROQ_API_KEY."}><i /> {health.isLoading ? "Connecting" : "Setup needed"}</span>
            )}
            <button className="icon-button context-toggle" onClick={toggleContext} title={contextCollapsed ? "Show chat context" : "Hide chat context"} aria-label="Toggle context panel">
              {contextCollapsed ? <PanelRightOpen size={17} /> : <PanelRightClose size={17} />}
            </button>
          </div>
        </header>
        {apiError && <div className="api-banner" role="status">{apiError}<button onClick={() => health.refetch()}>Retry</button></div>}
        <div className="workspace-grid">
          <section className="center-panel">
            <Routes>
              <Route path="/chat" element={<ChatWorkspace chat={activeChat} health={health.data} />} />
              <Route path="/documents" element={<DocumentsPage chat={activeChat} />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          </section>
          {!contextCollapsed && (
            <ContextPanel chat={activeChat} />
          )}
        </div>
        {projects.isError && <span className="sr-only">Projects could not be loaded.</span>}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
