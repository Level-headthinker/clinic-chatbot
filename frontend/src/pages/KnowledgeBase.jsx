import { useCallback, useEffect, useState } from "react";
import {
  BookOpen, Plus, Pencil, Trash2, Search, Sparkles, X, Check, Tag,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const EMPTY = { question: "", answer: "", category: "", is_active: true };

export default function KnowledgeBase() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState(null);   // null | EMPTY | entry
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [testQ, setTestQ] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const { notify } = useToast();

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/knowledge");
      setEntries(res.data);
    } catch {
      notify("Failed to load the knowledge base.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const save = async () => {
    if (!editor.question.trim() || !editor.answer.trim()) {
      notify("Both a question and an answer are required.", "error");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        question: editor.question.trim(),
        answer: editor.answer.trim(),
        category: editor.category.trim() || null,
        is_active: editor.is_active,
      };
      if (editor.id) await api.put(`/knowledge/${editor.id}`, payload);
      else await api.post("/knowledge", payload);
      notify(editor.id ? "Entry updated." : "Entry added.", "success");
      setEditor(null);
      fetchEntries();
    } catch (e) {
      notify(e.response?.data?.detail || "Could not save the entry.", "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (entry) => {
    if (!window.confirm(`Delete "${entry.question}"?`)) return;
    try {
      await api.delete(`/knowledge/${entry.id}`);
      notify("Entry deleted.", "success");
      fetchEntries();
    } catch {
      notify("Could not delete the entry.", "error");
    }
  };

  const runTest = async () => {
    if (!testQ.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.get(`/knowledge/test`, { params: { q: testQ.trim() } });
      setTestResult(res.data.matches);
    } catch {
      notify("Test failed.", "error");
    } finally {
      setTesting(false);
    }
  };

  const filtered = entries.filter((e) => {
    if (!search.trim()) return true;
    const s = search.toLowerCase();
    return e.question.toLowerCase().includes(s) || e.answer.toLowerCase().includes(s) || (e.category || "").toLowerCase().includes(s);
  });

  return (
    <AppLayout
      title="Knowledge Base"
      subtitle="Teach your bot answers to common patient questions. It uses these automatically when a patient asks something relevant."
      actions={
        <button className="btn btn-primary" onClick={() => setEditor({ ...EMPTY })}>
          <Plus size={16} /> Add entry
        </button>
      }
    >
      {/* Test retrieval */}
      <section className="table-panel" style={{ marginBottom: 16 }}>
        <div className="panel-header">
          <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Sparkles size={18} /> Try it
          </h2>
        </div>
        <div style={{ padding: 16 }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Type a patient question to see what the bot would pull from your knowledge base.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input
              className="input" style={{ flex: 1, minWidth: 220 }}
              placeholder="e.g. how should I prepare for a chemical peel?"
              value={testQ}
              onChange={(e) => setTestQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runTest()}
            />
            <button className="btn btn-secondary" onClick={runTest} disabled={testing || !testQ.trim()}>
              <Search size={16} /> {testing ? "Searching…" : "Test"}
            </button>
          </div>
          {testResult && (
            <div style={{ marginTop: 12 }}>
              {testResult.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>No match — the bot would fall back to "please contact the clinic."</p>
              ) : (
                testResult.map((m, i) => (
                  <div key={i} style={matchBox}>
                    <strong>{m.question}</strong>
                    <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>{m.answer}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </section>

      {/* List */}
      <section className="table-panel">
        <div className="panel-header">
          <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <BookOpen size={18} /> Entries
          </h2>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input className="input" style={{ width: 200 }} placeholder="Search…" value={search} onChange={(e) => setSearch(e.target.value)} />
            <span className="badge">{entries.length}</span>
          </div>
        </div>

        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title={entries.length === 0 ? "No knowledge yet" : "No matches"}
            description={entries.length === 0
              ? "Add Q&As like pricing, pre-care instructions, parking, or insurance — the bot will use them automatically."
              : "Try a different search."}
            action={entries.length === 0 ? <button className="btn btn-primary" onClick={() => setEditor({ ...EMPTY })}><Plus size={16} /> Add your first entry</button> : null}
          />
        ) : (
          <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map((e) => (
              <article key={e.id} style={card}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 15 }}>{e.question}</strong>
                    {e.category && (
                      <span className="badge" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        <Tag size={11} /> {e.category}
                      </span>
                    )}
                    {!e.is_active && <span className="badge badge-danger" style={{ fontSize: 10 }}>Off</span>}
                  </div>
                  <p style={{ margin: "6px 0 0", color: "var(--muted)", fontSize: 13, lineHeight: 1.5 }}>{e.answer}</p>
                </div>
                <div className="action-row" style={{ flexShrink: 0 }}>
                  <button className="icon-btn" title="Edit" onClick={() => setEditor(e)}><Pencil size={15} /></button>
                  <button className="icon-btn" title="Delete" onClick={() => remove(e)}><Trash2 size={15} /></button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Editor modal */}
      {editor && (
        <div style={scrim} onClick={() => !saving && setEditor(null)}>
          <div style={modal} onClick={(ev) => ev.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>{editor.id ? "Edit entry" : "Add entry"}</h2>
              <button className="icon-btn" onClick={() => setEditor(null)}><X size={18} /></button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="field">
                <label>Question / topic</label>
                <input className="input" placeholder="What should I do before a chemical peel?"
                  value={editor.question} onChange={(e) => setEditor({ ...editor, question: e.target.value })} autoFocus />
              </div>
              <div className="field">
                <label>Answer</label>
                <textarea className="input" rows={4} placeholder="Avoid sun exposure and stop retinol 3 days before…"
                  value={editor.answer} onChange={(e) => setEditor({ ...editor, answer: e.target.value })} />
              </div>
              <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
                <div className="field" style={{ flex: 1, minWidth: 160 }}>
                  <label>Category (optional)</label>
                  <input className="input" placeholder="Pricing, Pre-care, General…"
                    value={editor.category} onChange={(e) => setEditor({ ...editor, category: e.target.value })} />
                </div>
                <div className="field" style={{ display: "flex", alignItems: "flex-end" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", paddingBottom: 8 }}>
                    <input type="checkbox" checked={editor.is_active} onChange={(e) => setEditor({ ...editor, is_active: e.target.checked })} />
                    Active (bot uses it)
                  </label>
                </div>
              </div>
            </div>
            <div className="action-row" style={{ marginTop: 18, justifyContent: "flex-end" }}>
              <button className="btn btn-secondary" onClick={() => setEditor(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={save} disabled={saving}>
                <Check size={16} /> {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

const card = {
  display: "flex", gap: 12, alignItems: "flex-start",
  padding: "14px 16px", border: "1px solid var(--line)", borderRadius: 10,
  background: "var(--surface)",
};
const matchBox = {
  padding: "10px 14px", borderLeft: "3px solid var(--accent, #0d9488)",
  background: "var(--surface-2)", borderRadius: 8, marginBottom: 8, fontSize: 14,
};
const scrim = {
  position: "fixed", inset: 0, background: "rgba(0,0,0,.45)",
  display: "grid", placeItems: "center", zIndex: 1000, padding: 16,
};
const modal = {
  background: "var(--surface)", borderRadius: 14, padding: 22,
  width: "100%", maxWidth: 560, maxHeight: "90vh", overflowY: "auto",
  boxShadow: "0 12px 40px rgba(0,0,0,.25)",
};
