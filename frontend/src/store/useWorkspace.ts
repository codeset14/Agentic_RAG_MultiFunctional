import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatFilter, Page } from "../types";

interface WorkspaceState {
  activeChatId: string | null;
  activeProjectId: string | null;
  page: Page;
  filter: ChatFilter;
  search: string;
  sidebarCollapsed: boolean;
  contextCollapsed: boolean;
  queuedPrompt: string | null;
  setActiveChat: (chatId: string, projectId?: string) => void;
  setPage: (page: Page) => void;
  setFilter: (filter: ChatFilter) => void;
  setSearch: (search: string) => void;
  toggleSidebar: () => void;
  toggleContext: () => void;
  queuePrompt: (prompt: string) => void;
  clearQueuedPrompt: () => void;
}

export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set) => ({
      activeChatId: null,
      activeProjectId: null,
      page: "chat",
      filter: "all",
      search: "",
      sidebarCollapsed: false,
      contextCollapsed: false,
      queuedPrompt: null,
      setActiveChat: (activeChatId, activeProjectId) =>
        set({ activeChatId, activeProjectId }),
      setPage: (page) => set({ page }),
      setFilter: (filter) => set({ filter }),
      setSearch: (search) => set({ search }),
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      toggleContext: () =>
        set((state) => ({ contextCollapsed: !state.contextCollapsed })),
      queuePrompt: (queuedPrompt) => set({ queuedPrompt, page: "chat" }),
      clearQueuedPrompt: () => set({ queuedPrompt: null }),
    }),
    {
      name: "agentic-rag-workspace",
      partialize: (state) => ({
        activeChatId: state.activeChatId,
        activeProjectId: state.activeProjectId,
        page: state.page,
        filter: state.filter,
        sidebarCollapsed: state.sidebarCollapsed,
        contextCollapsed: state.contextCollapsed,
      }),
    },
  ),
);
