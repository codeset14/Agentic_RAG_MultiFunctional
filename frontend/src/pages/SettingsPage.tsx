import { useEffect, useState } from "react";
import { Check, KeyRound, Moon, Search, Settings2, Sun, WandSparkles } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getErrorMessage, workspaceApi } from "../lib/api";
import type { Preferences } from "../types";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: workspaceApi.preferences });
  const [draft, setDraft] = useState<Partial<Preferences>>({});
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (query.data) setDraft(query.data);
  }, [query.data]);
  const update = useMutation({
    mutationFn: () => workspaceApi.updatePreferences({
      theme: draft.theme,
      top_k: draft.top_k,
      max_iterations: draft.max_iterations,
    }),
    onSuccess: async (preferences) => {
      setDraft(preferences);
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
      window.setTimeout(() => setSaved(false), 1800);
    },
  });

  if (query.isLoading) return <div className="loading-inline">Loading preferences…</div>;
  if (query.isError) return <div className="inline-error">{getErrorMessage(query.error)}</div>;
  const preferences = query.data!;

  return (
    <div className="page-scroll settings-page">
      <header className="page-title-block">
        <div className="page-title-icon"><Settings2 size={19} /></div>
        <div><h1>Settings</h1><p>Manage your local workspace and retrieval preferences.</p></div>
      </header>
      <section className="settings-card">
        <div className="settings-card-heading"><span className="settings-icon"><Sun size={18} /></span><div><h2>Appearance</h2><p>Choose the theme that feels right for your workspace.</p></div></div>
        <div className="theme-choice-row">
          <button className={`theme-option ${draft.theme === "Light" ? "theme-option-selected" : ""}`} onClick={() => setDraft({ ...draft, theme: "Light" })}><Sun size={19} /><span><b>Light</b><small>Clean and bright</small></span>{draft.theme === "Light" && <Check size={16} />}</button>
          <button className={`theme-option ${draft.theme === "Dark" ? "theme-option-selected" : ""}`} onClick={() => setDraft({ ...draft, theme: "Dark" })}><Moon size={19} /><span><b>Dark</b><small>Easy on the eyes</small></span>{draft.theme === "Dark" && <Check size={16} />}</button>
        </div>
      </section>
      <section className="settings-card">
        <div className="settings-card-heading"><span className="settings-icon settings-icon-blue"><Search size={18} /></span><div><h2>Retrieval preferences</h2><p>These settings control how the existing RAG pipeline finds evidence.</p></div></div>
        <label className="setting-slider"><span><b>Search results (Top-K)</b><small>Number of evidence chunks considered per search.</small></span><strong>{draft.top_k}</strong><input type="range" min={3} max={20} value={draft.top_k ?? 8} onChange={(event) => setDraft({ ...draft, top_k: Number(event.target.value) })} /></label>
        <label className="setting-slider"><span><b>Validation iterations</b><small>Maximum retrieval refinement attempts for complex questions.</small></span><strong>{draft.max_iterations}</strong><input type="range" min={1} max={6} value={draft.max_iterations ?? 3} onChange={(event) => setDraft({ ...draft, max_iterations: Number(event.target.value) })} /></label>
      </section>
      <section className="settings-card">
        <div className="settings-card-heading"><span className="settings-icon settings-icon-purple"><WandSparkles size={18} /></span><div><h2>Model configuration</h2><p>Using the model choices already configured by the backend.</p></div></div>
        <div className="settings-model-list">
          <div><span>Language model</span><strong>{preferences.model}</strong></div>
          <div><span>Embedding model</span><strong>{preferences.embedding_model}</strong></div>
          <div><span>Reranker</span><strong>{preferences.reranker_model}</strong></div>
        </div>
        <div className={`key-config-notice ${preferences.api_key_configured ? "key-configured" : "key-missing"}`}><KeyRound size={16} /><span>{preferences.api_key_configured ? "API key is configured in the backend environment. Secret values are never sent to this page." : "GROQ_API_KEY is not configured in the backend .env file."}</span></div>
      </section>
      <section className="settings-card settings-not-configured">
        <div className="settings-card-heading"><span className="settings-icon"><Settings2 size={18} /></span><div><h2>Not configured</h2><p>Accounts, web search, streaming generation, and cloud sync are not present in the existing backend.</p></div></div>
      </section>
      {update.isError && <div className="inline-error">{getErrorMessage(update.error)}</div>}
      <div className="settings-save-row"><span>{saved ? <><Check size={15} /> Preferences saved</> : "Changes are stored on this device."}</span><button className="button button-primary" disabled={update.isPending} onClick={() => update.mutate()}>{update.isPending ? "Saving…" : "Save preferences"}</button></div>
    </div>
  );
}
