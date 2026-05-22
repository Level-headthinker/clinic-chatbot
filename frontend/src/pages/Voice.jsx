import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  ExternalLink,
  Phone,
  PhoneCall,
  PhoneIncoming,
  PhoneMissed,
  PhoneOff,
  Send,
  Settings,
  XCircle,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useToast } from "../context/ToastContext";

// ── helpers ────────────────────────────────────────────────────────────────────

function durationLabel(secs) {
  if (!secs) return "-";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function callStatusBadge(status) {
  const map = {
    ended: "badge-success",
    "in-progress": "badge-primary",
    queued: "badge badge-warning",
    ringing: "badge-warning",
    failed: "badge-danger",
    "no-answer": "badge-danger",
    busy: "badge-danger",
  };
  return map[status] || "";
}

function CallIcon({ status }) {
  if (status === "ended") return <PhoneIncoming size={15} style={{ color: "var(--success)" }} />;
  if (status === "failed" || status === "no-answer" || status === "busy")
    return <PhoneMissed size={15} style={{ color: "var(--danger)" }} />;
  if (status === "in-progress") return <PhoneCall size={15} style={{ color: "var(--primary)" }} />;
  return <PhoneOff size={15} style={{ color: "var(--muted)" }} />;
}

const SETUP_STEPS = [
  {
    n: 1,
    title: "Create a VAPI account",
    body: "Go to vapi.ai and sign up. Free tier includes 10 minutes of calls per month.",
    link: "https://vapi.ai",
    linkLabel: "vapi.ai →",
  },
  {
    n: 2,
    title: "Add a phone number",
    body: "In the VAPI dashboard, go to Phone Numbers and buy a number (~$2/month). Copy the Phone Number ID.",
    link: null,
  },
  {
    n: 3,
    title: "Get your API key",
    body: "In VAPI dashboard → Account → API Keys. Copy your private key.",
    link: null,
  },
  {
    n: 4,
    title: "Update your .env",
    body: "Add these three variables to backend/.env:",
    code: `VAPI_API_KEY=your-vapi-api-key
VAPI_PHONE_NUMBER_ID=your-phone-number-id
VOICE_BRANCH_SLUG=your-branch-slug`,
  },
  {
    n: 5,
    title: "Set the Server URL in VAPI",
    body: "In VAPI dashboard → Phone Numbers → your number → Server URL, enter your backend URL:",
    code: "https://your-domain.com/voice/vapi-server",
  },
];

// ── component ──────────────────────────────────────────────────────────────────

export default function Voice() {
  const [status, setStatus] = useState(null);
  const [calls, setCalls] = useState([]);
  const [loadingCalls, setLoadingCalls] = useState(false);
  const [callForm, setCallForm] = useState({
    patient_phone: "",
    patient_name: "",
    first_message: "",
  });
  const [calling, setCalling] = useState(false);
  const [tab, setTab] = useState("calls"); // "calls" | "setup"
  const { notify } = useToast();

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get("/voice/status");
      setStatus(res.data);
    } catch {
      setStatus({ configured: false });
    }
  }, []);

  const fetchCalls = useCallback(async () => {
    setLoadingCalls(true);
    try {
      const res = await api.get("/voice/calls");
      setCalls(res.data.calls || []);
    } catch {
      notify("Failed to load call history.", "error");
    } finally {
      setLoadingCalls(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (tab === "calls") fetchCalls();
  }, [tab, fetchCalls]);

  const makeCall = async (e) => {
    e.preventDefault();
    if (!callForm.patient_phone.trim()) return;
    setCalling(true);
    try {
      await api.post("/voice/outbound", callForm);
      notify(`Call started to ${callForm.patient_phone}`, "success");
      setCallForm({ patient_phone: "", patient_name: "", first_message: "" });
      setTimeout(fetchCalls, 3000);
    } catch (err) {
      const detail = err.response?.data?.error || "Failed to start call.";
      notify(detail, "error");
    } finally {
      setCalling(false);
    }
  };

  const isConfigured = status?.configured;

  return (
    <AppLayout
      title="Voice Agent"
      subtitle="VAPI-powered AI voice calls — inbound clinic calls and outbound patient follow-ups."
    >
      {/* Status banner */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "12px 16px",
          borderRadius: "var(--radius-md)",
          background: isConfigured ? "var(--success-soft)" : "var(--warning-soft)",
          border: `1px solid ${isConfigured ? "var(--success-border)" : "var(--warning-border)"}`,
          marginBottom: 20,
        }}
      >
        {isConfigured ? (
          <CheckCircle2 size={18} style={{ color: "var(--success)", flexShrink: 0 }} />
        ) : (
          <XCircle size={18} style={{ color: "var(--warning)", flexShrink: 0 }} />
        )}
        <div>
          <p style={{ fontWeight: 600, color: isConfigured ? "var(--success)" : "var(--warning)", marginBottom: 0 }}>
            {isConfigured ? "VAPI is connected" : "VAPI is not configured yet"}
          </p>
          {!isConfigured && (
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
              {!status?.has_api_key && "Missing VAPI_API_KEY. "}
              {!status?.has_phone_number && "Missing VAPI_PHONE_NUMBER_ID. "}
              See the Setup Guide tab below.
            </p>
          )}
          {isConfigured && status?.branch_slug && (
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
              Answering calls for branch: <strong>{status.branch_slug}</strong>
            </p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid var(--line)", paddingBottom: 0 }}>
        {[
          { key: "calls", label: "Call History", icon: Phone },
          { key: "outbound", label: "Make a Call", icon: PhoneCall },
          { key: "setup", label: "Setup Guide", icon: Settings },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "9px 14px",
              borderRadius: "var(--radius) var(--radius) 0 0",
              border: "1px solid transparent",
              borderBottom: tab === key ? "2px solid var(--primary)" : "1px solid transparent",
              background: tab === key ? "var(--primary-soft)" : "transparent",
              color: tab === key ? "var(--primary)" : "var(--muted)",
              fontWeight: tab === key ? 600 : 500,
              fontSize: 13.5,
              cursor: "pointer",
              transition: "all var(--t-fast)",
            }}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* ── Call History tab ── */}
      {tab === "calls" && (
        <section className="table-panel">
          <div className="panel-header">
            <h2>Recent calls</h2>
            <button className="btn btn-secondary" onClick={fetchCalls} disabled={loadingCalls}>
              {loadingCalls ? "Loading…" : "Refresh"}
            </button>
          </div>
          {loadingCalls ? (
            <div className="empty-state">
              <Clock size={24} style={{ color: "var(--muted)", marginBottom: 8 }} />
              <p>Loading calls…</p>
            </div>
          ) : calls.length === 0 ? (
            <div className="empty-state">
              <div className="empty-mark">
                <Phone size={24} />
              </div>
              <h3>No calls yet</h3>
              <p>
                {isConfigured
                  ? "Calls will appear here once your VAPI phone number receives its first call."
                  : "Configure VAPI first using the Setup Guide tab."}
              </p>
            </div>
          ) : (
            <table className="responsive-table">
              <thead>
                <tr>
                  {["", "Direction", "Caller", "Duration", "Status", "Started"].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {calls.map((call) => (
                  <tr key={call.id}>
                    <td data-label="">
                      <CallIcon status={call.status} />
                    </td>
                    <td data-label="Direction">
                      <span className="badge">
                        {call.type === "outboundPhoneCall" ? "Outbound" : "Inbound"}
                      </span>
                    </td>
                    <td data-label="Caller">
                      <strong>{call.customer?.name || "—"}</strong>
                      <br />
                      <span className="muted" style={{ fontSize: 12 }}>
                        {call.customer?.number || ""}
                      </span>
                    </td>
                    <td data-label="Duration">{durationLabel(call.endedReason === "silence-timed-out" ? 0 : call.duration)}</td>
                    <td data-label="Status">
                      <span className={`badge ${callStatusBadge(call.status)}`}>{call.status}</span>
                    </td>
                    <td data-label="Started">
                      {call.startedAt
                        ? new Date(call.startedAt).toLocaleString()
                        : call.createdAt
                        ? new Date(call.createdAt).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* ── Make a Call tab ── */}
      {tab === "outbound" && (
        <section className="form-panel">
          <h3>Make an outbound call</h3>
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 18, marginTop: -10 }}>
            The AI will call the patient's phone number and have a conversation using your clinic context.
          </p>
          <form onSubmit={makeCall} className="form-stack">
            <div className="form-grid">
              <div className="field">
                <label>Patient phone *</label>
                <input
                  className="input"
                  placeholder="+923001234567 or 03001234567"
                  value={callForm.patient_phone}
                  onChange={(e) => setCallForm({ ...callForm, patient_phone: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>Patient name</label>
                <input
                  className="input"
                  placeholder="Ali Khan"
                  value={callForm.patient_name}
                  onChange={(e) => setCallForm({ ...callForm, patient_name: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label>Custom opening message (optional)</label>
              <input
                className="input"
                placeholder="Hello! This is City Clinic calling about your upcoming appointment…"
                value={callForm.first_message}
                onChange={(e) => setCallForm({ ...callForm, first_message: e.target.value })}
              />
              <p style={{ fontSize: 11, color: "var(--muted)", margin: "4px 0 0" }}>
                Leave blank to use the default clinic greeting.
              </p>
            </div>
            <div className="action-row">
              <button
                className="btn btn-primary"
                type="submit"
                disabled={calling || !isConfigured}
              >
                <Send size={15} />
                {calling ? "Calling…" : "Start call"}
              </button>
              {!isConfigured && (
                <span style={{ fontSize: 12, color: "var(--warning)" }}>
                  VAPI must be configured first.
                </span>
              )}
            </div>
          </form>
        </section>
      )}

      {/* ── Setup Guide tab ── */}
      {tab === "setup" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {SETUP_STEPS.map((step) => (
            <div key={step.n} className="timeline-card">
              <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "var(--primary)",
                    color: "#fff",
                    display: "grid",
                    placeItems: "center",
                    fontSize: 13,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {step.n}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>
                    {step.title}
                  </p>
                  <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: step.code ? 10 : 0 }}>
                    {step.body}
                  </p>
                  {step.code && (
                    <pre
                      style={{
                        background: "var(--surface-2)",
                        border: "1px solid var(--line)",
                        borderRadius: "var(--radius)",
                        padding: "10px 14px",
                        fontSize: 12,
                        color: "var(--text-2)",
                        overflowX: "auto",
                        margin: 0,
                        fontFamily: "monospace",
                      }}
                    >
                      {step.code}
                    </pre>
                  )}
                  {step.link && (
                    <a
                      href={step.link}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        fontSize: 13,
                        color: "var(--primary)",
                        fontWeight: 600,
                        marginTop: 6,
                      }}
                    >
                      {step.linkLabel} <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}

          <div
            style={{
              background: "var(--primary-soft)",
              border: "1px solid var(--primary-border)",
              borderRadius: "var(--radius-md)",
              padding: "14px 18px",
            }}
          >
            <p style={{ fontWeight: 600, color: "var(--primary-text)", marginBottom: 4 }}>
              WhatsApp — Meta Cloud API
            </p>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>
              WhatsApp messages (from the Communication Log in patient records) now use the Meta Cloud API.
              Free for 1,000 conversations/month. Add{" "}
              <code style={{ fontFamily: "monospace", background: "var(--surface-2)", padding: "1px 5px", borderRadius: 4 }}>
                META_PHONE_NUMBER_ID
              </code>{" "}
              and{" "}
              <code style={{ fontFamily: "monospace", background: "var(--surface-2)", padding: "1px 5px", borderRadius: 4 }}>
                META_ACCESS_TOKEN
              </code>{" "}
              to your <code style={{ fontFamily: "monospace", background: "var(--surface-2)", padding: "1px 5px", borderRadius: 4 }}>.env</code> to enable it.
            </p>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
