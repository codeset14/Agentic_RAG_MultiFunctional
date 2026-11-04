import axios from "axios";
import type {
  Analytics,
  Chat,
  ChatMessage,
  Health,
  Preferences,
  Project,
  WorkspaceDocument,
} from "../types";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 120_000,
});

declare module "axios" {
  export interface InternalAxiosRequestConfig {
    workspaceAuthAttempts?: number;
  }
}

let passwordPrompt: Promise<string | null> | null = null;

function requestWorkspacePassword(): Promise<string | null> {
  if (!passwordPrompt) {
    passwordPrompt = Promise.resolve(
      window.prompt("Enter the workspace password to continue."),
    ).finally(() => {
      passwordPrompt = null;
    });
  }
  return passwordPrompt;
}

api.interceptors.request.use((config) => {
  const password = sessionStorage.getItem("workspace-password");
  if (password) config.headers.set("X-Workspace-Password", password);
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || error.response?.status !== 401 || !error.config) {
      return Promise.reject(error);
    }

    const config = error.config;
    const attempts = config.workspaceAuthAttempts ?? 0;
    if (attempts >= 2) {
      sessionStorage.removeItem("workspace-password");
      return Promise.reject(new Error("Incorrect workspace password."));
    }
    if (attempts > 0) sessionStorage.removeItem("workspace-password");

    const password =
      sessionStorage.getItem("workspace-password") ?? await requestWorkspacePassword();
    if (!password) return Promise.reject(new Error("Workspace password is required."));

    sessionStorage.setItem("workspace-password", password);
    config.workspaceAuthAttempts = attempts + 1;
    config.headers.set("X-Workspace-Password", password);
    return api.request(config);
  },
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    return error.message || "The API could not be reached.";
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}

export const workspaceApi = {
  health: async () => (await api.get<Health>("/health")).data,
  projects: async () => (await api.get<Project[]>("/projects")).data,
  deletedProjects: async () => (await api.get<Project[]>("/projects/trash")).data,
  createProject: async (name: string, description: string) =>
    (await api.post<Project>("/projects", { name, description })).data,
  updateProject: async (
    projectId: string,
    patch: { name?: string; description?: string },
  ) => (await api.patch<Project>(`/projects/${projectId}`, patch)).data,
  deleteProject: async (projectId: string) =>
    api.delete(`/projects/${projectId}`),
  restoreProject: async (projectId: string) =>
    (await api.post<Project>(`/projects/${projectId}/restore`)).data,
  chats: async (params: {
    project_id?: string;
    starred?: boolean;
    deleted?: boolean;
    search?: string;
  } = {}) => (await api.get<Chat[]>("/chats", { params })).data,
  createChat: async (projectId: string, title = "New Chat") =>
    (await api.post<Chat>("/chats", { project_id: projectId, title })).data,
  chat: async (chatId: string) => (await api.get<Chat>(`/chats/${chatId}`)).data,
  updateChat: async (
    chatId: string,
    patch: {
      title?: string;
      project_id?: string;
      is_starred?: boolean;
      is_deleted?: boolean;
    },
  ) => (await api.patch<Chat>(`/chats/${chatId}`, patch)).data,
  deleteChat: async (chatId: string) => api.delete(`/chats/${chatId}`),
  restoreChat: async (chatId: string) =>
    (await api.post<Chat>(`/chats/${chatId}/restore`)).data,
  duplicateChat: async (chatId: string) =>
    (await api.post<Chat>(`/chats/${chatId}/duplicate`)).data,
  messages: async (chatId: string) =>
    (await api.get<ChatMessage[]>(`/chats/${chatId}/messages`)).data,
  sendMessage: async (chatId: string, content: string) =>
    (
      await api.post<{ assistant_message: ChatMessage }>(
        `/chats/${chatId}/messages`,
        { content },
      )
    ).data,
  documents: async (chatId: string) =>
    (await api.get<WorkspaceDocument[]>(`/chats/${chatId}/documents`)).data,
  uploadDocuments: async (chatId: string, files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return (
      await api.post<WorkspaceDocument[]>(
        `/chats/${chatId}/documents`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      )
    ).data;
  },
  previewDocument: async (documentId: string) =>
    (
      await api.get<{ document_id: string; file_name: string; text: string }>(
        `/documents/${documentId}/preview`,
      )
    ).data,
  deleteDocument: async (documentId: string) =>
    api.delete(`/documents/${documentId}`),
  analytics: async () => (await api.get<Analytics>("/analytics")).data,
  preferences: async () => (await api.get<Preferences>("/settings")).data,
  updatePreferences: async (patch: Partial<Preferences>) =>
    (await api.patch<Preferences>("/settings", patch)).data,
  submitFeedback: async (messageId: string, feedback: "up" | "down") =>
    api.post(`/messages/${messageId}/feedback`, { feedback }),
};
