import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, Send, User, MessageSquare, Phone, ArrowLeft, Globe } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const POLL_MS = 5000;

export default function Conversations() {
  const [list, setList] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [filter, setFilter] = useState("all"); // all | whatsapp | web | human
  const [activeToken, setActiveToken] = useState(null);
  const [thread, setThread] = useState(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const { notify } = useToast();
  const bottomRef = useRef(null);

  const fetchList = useCallback(async () => {
    try {
      const params = {};
      if (filter === "whatsapp" || filter === "web") params.channel = filter;
      if (filter === "human") params.mode = "human";
      const res = await api.get("/conversations", { params });
      setList(res.data);
    } catch {
      // keep last list on transient errors (polling)
    } finally {
      setLoadingList(false);
    }
  }, [filter]);

  const fetchThread = useCallback(async (token) => {
    try {
      const res = await api.get(`/conversations/${encodeURIComponent(token)}`);
      setThread(res.data);
    } catch {
      notify("Could not load that conversation.", "error");
    }
  }, [notify]);

  useEffect(() => { fetchList(); }, [fetchList]);

  // Poll the list, and the open thread, so new patient messages appear live.
  useEffect(() => {
    const id = setInterval(() => {
      fetchList();
      if (activeToken) fetchThread(activeToken);
    }, POLL_MS);
    return () => clearInterval(id);
  }, [fetchList, fetchThread, activeToken]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.messages?.length]);

  const openConversation = async (token) => {
    setActiveToken(token);
    setThread(null);
    await fetchThread(token);
    fetchList(); // unread badge cleared server-side on open
  };

  const setMode = async (token, human) => {
    try {
      await api.post(`/conversations/${encodeURIComponent(token)}/${human ? "takeover" : "handback"}`);
      setThread((t) => (t ? { ...t, human_handling: human } : t));
      fetchList();
      notify(human ? "You're now handling this chat — the bot is paused." : "Handed back to the bot.", "success");
    } catch {
      notify("Could not change mode.", "error");
    }
  };

  const sendReply = async () => {
    if (!reply.trim() || !thread) return;
    setSending(true);
    try {
      await api.post(`/conversations/${encodeURIComponent(thread.session_token)}/reply`, { message: reply.trim() });
      setReply("");
      await fetchThread(thread.session_token);
    } catch (e) {
      notify(e.response?.data?.detail || "Could not send the message.", "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <AppLayout
      title="Conversations"
      subtitle="Your shared WhatsApp inbox — the bot replies automatically, take over any chat to reply yourself."
      actions={
        <select className="select" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All chats</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="web">Web widget</option>
          <option value="human">Needs me (human)</option>
        </select>
      }
    >
      <div className={`inbox-grid${activeToken ? " has-active" : ""}`} style={inboxGrid()}>
        {/* ── Conversation list ── */}
        <section className="table-panel inbox-list">
          <div className="panel-header">
            <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <MessageSquare size={18} /> Inbox
            </h2>
            <span className="badge">{list.length}</span>
          </div>
          {loadingList ? (
            <SkeletonBlock className="skeleton-table" />
          ) : list.length === 0 ? (
            <EmptyState icon={MessageSquare} title="No conversations" description="Patient chats will appear here as they message your number." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {list.map((c) => (
                <button
                  key={c.session_token}
                  onClick={() => openConversation(c.session_token)}
                  className="inbox-row"
                  style={inboxRow(c.session_token === activeToken)}
                >
                  <div style={avatarStyle(c.channel)}>
                    {c.channel === "whatsapp" ? <Phone size={15} /> : <Globe size={15} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {c.patient_name}
                      </strong>
                      {c.human_handling
                        ? <span className="badge badge-warning" style={{ fontSize: 10 }}>Human</span>
                        : <span className="badge" style={{ fontSize: 10 }}>Bot</span>}
                    </div>
                    <p className="muted" style={{ margin: "2px 0 0", fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {c.last_role === "assistant" ? "↩ " : ""}{c.last_message || "—"}
                    </p>
                  </div>
                  {c.unread > 0 && <span style={unreadDot}>{c.unread}</span>}
                </button>
              ))}
            </div>
          )}
        </section>

        {/* ── Thread ── */}
        <section className="table-panel inbox-thread" style={{ flexDirection: "column", minHeight: 480 }}>
          {!activeToken ? (
            <div style={{ flex: 1, display: "grid", placeItems: "center", color: "var(--muted)", padding: 24, textAlign: "center" }}>
              <div>
                <MessageSquare size={28} style={{ opacity: 0.5 }} />
                <p style={{ marginTop: 8 }}>Select a conversation to read and reply.</p>
              </div>
            </div>
          ) : !thread ? (
            <div style={{ flex: 1, display: "grid", placeItems: "center", color: "var(--muted)" }}>
              <SkeletonBlock className="skeleton-table" />
            </div>
          ) : (
            <>
              <div className="panel-header" style={{ gap: 8 }}>
                <button className="icon-btn inbox-back" onClick={() => { setActiveToken(null); setThread(null); }} aria-label="Back">
                  <ArrowLeft size={18} />
                </button>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h2 style={{ margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {thread.patient_name || thread.patient_phone || "Conversation"}
                  </h2>
                  <p className="muted" style={{ margin: 0, fontSize: 12 }}>
                    {thread.channel === "whatsapp" ? "WhatsApp" : "Web widget"}
                    {thread.patient_phone ? ` · ${thread.patient_phone}` : ""}
                  </p>
                </div>
                {thread.human_handling ? (
                  <button className="btn btn-secondary" onClick={() => setMode(thread.session_token, false)}>
                    <Bot size={16} /> Hand back to bot
                  </button>
                ) : (
                  <button className="btn btn-primary" onClick={() => setMode(thread.session_token, true)}>
                    <User size={16} /> Take over
                  </button>
                )}
              </div>

              <div style={{ flex: 1, overflowY: "auto", padding: 16, background: "var(--bg)", display: "flex", flexDirection: "column", gap: 8 }}>
                {(thread.messages || []).map((m, i) => (
                  <Bubble key={i} msg={m} />
                ))}
                <div ref={bottomRef} />
              </div>

              {thread.channel === "whatsapp" ? (
                <div style={{ padding: 12, borderTop: "1px solid var(--line)", display: "flex", gap: 8 }}>
                  {!thread.human_handling && (
                    <span className="muted" style={{ fontSize: 12, alignSelf: "center" }}>
                      Tip: “Take over” to pause the bot before replying.
                    </span>
                  )}
                  <input
                    className="input"
                    style={{ flex: 1 }}
                    placeholder="Type a reply…"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendReply(); } }}
                  />
                  <button className="btn btn-primary" onClick={sendReply} disabled={sending || !reply.trim()}>
                    <Send size={16} /> {sending ? "…" : "Send"}
                  </button>
                </div>
              ) : (
                <div style={{ padding: 12, borderTop: "1px solid var(--line)", color: "var(--muted)", fontSize: 13 }}>
                  This is a web-widget chat — there's no WhatsApp channel to reply on.
                </div>
              )}
            </>
          )}
        </section>
      </div>

      <style>{INBOX_CSS}</style>
    </AppLayout>
  );
}

function Bubble({ msg }) {
  const isUser = msg.role === "user";
  const byAgent = msg.by === "agent";
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-start" : "flex-end" }}>
      <div style={{
        maxWidth: "76%", padding: "8px 12px", borderRadius: 12, fontSize: 14, lineHeight: 1.4,
        background: isUser ? "var(--surface)" : byAgent ? "#dcfce7" : "var(--accent, #0d9488)",
        color: isUser ? "var(--text-1)" : byAgent ? "#065f46" : "#fff",
        border: isUser ? "1px solid var(--line)" : "none",
        whiteSpace: "pre-wrap", wordBreak: "break-word",
      }}>
        {!isUser && (
          <div style={{ fontSize: 10, fontWeight: 700, opacity: 0.8, marginBottom: 2 }}>
            {byAgent ? `👤 ${msg.agent || "Staff"}` : "🤖 Bot"}
          </div>
        )}
        {msg.content}
      </div>
    </div>
  );
}

const inboxGrid = () => ({
  display: "grid",
  gridTemplateColumns: "minmax(280px, 360px) 1fr",
  gap: 16,
  alignItems: "start",
});

const inboxRow = (active) => ({
  display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
  border: "none", borderBottom: "1px solid var(--line)", width: "100%",
  background: active ? "var(--surface-2)" : "transparent", cursor: "pointer", textAlign: "left",
});

const avatarStyle = (channel) => ({
  width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
  display: "grid", placeItems: "center", color: "#fff",
  background: channel === "whatsapp" ? "#25d366" : "#6366f1",
});

const unreadDot = {
  background: "#ef4444", color: "#fff", borderRadius: 10, fontSize: 11, fontWeight: 800,
  minWidth: 20, height: 20, padding: "0 6px", display: "grid", placeItems: "center",
};

// Desktop: list + thread side by side. Mobile: show list OR thread, with a
// back button to return to the list.
const INBOX_CSS = `
.inbox-back { display: none; }
@media (max-width: 760px) {
  .inbox-grid { grid-template-columns: 1fr !important; }
  .inbox-grid .inbox-thread { display: none !important; }
  .inbox-grid.has-active .inbox-list { display: none !important; }
  .inbox-grid.has-active .inbox-thread { display: flex !important; }
  .inbox-back { display: inline-flex !important; }
}
`;
