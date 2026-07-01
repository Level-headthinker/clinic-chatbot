import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2, Circle, Bot, Building2, Stethoscope, MessageCircle, PlayCircle, PartyPopper,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const ICONS = {
  profile: Bot,
  branch: Building2,
  doctors: Stethoscope,
  whatsapp: MessageCircle,
  test: PlayCircle,
};

export default function Onboarding() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { notify } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/onboarding/status");
      setStatus(res.data);
    } catch {
      notify("Could not load your setup progress.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { load(); }, [load]);

  const dismiss = async () => {
    try {
      await api.post("/onboarding/dismiss");
      notify("Setup guide hidden. You can finish anytime from Settings.", "success");
      navigate("/dashboard");
    } catch {
      notify("Something went wrong.", "error");
    }
  };

  const pct = status && status.total_required
    ? Math.round((status.completed_required / status.total_required) * 100)
    : 0;

  return (
    <AppLayout
      title="Getting started"
      subtitle="A few quick steps to get your clinic's AI assistant live."
    >
      {loading ? (
        <SkeletonBlock className="panel skeleton-table" />
      ) : !status ? null : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 760 }}>

          {/* Progress header */}
          <div className="panel" style={{ padding: "18px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {status.completed
                  ? <PartyPopper size={22} style={{ color: "var(--success, #16a34a)" }} />
                  : <Bot size={22} style={{ color: "var(--primary)" }} />}
                <strong style={{ fontSize: 16 }}>
                  {status.completed
                    ? "You're all set — your bot is ready!"
                    : `${status.completed_required} of ${status.total_required} essential steps done`}
                </strong>
              </div>
              <span className="badge">{pct}%</span>
            </div>
            <div style={{ marginTop: 12, height: 8, borderRadius: 6, background: "var(--surface-2, #eee)", overflow: "hidden" }}>
              <div style={{
                width: `${pct}%`, height: "100%", borderRadius: 6,
                background: status.completed ? "var(--success, #16a34a)" : "var(--primary)",
                transition: "width .3s",
              }} />
            </div>
          </div>

          {/* Steps */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {status.steps.map((step) => {
              const Icon = ICONS[step.key] || Circle;
              return (
                <div key={step.key} className="panel" style={{
                  display: "flex", alignItems: "center", gap: 14, padding: "16px 18px",
                  opacity: step.done ? 0.75 : 1,
                }}>
                  <span style={{
                    flexShrink: 0, width: 40, height: 40, borderRadius: 10, display: "grid", placeItems: "center",
                    background: step.done ? "rgba(22,163,74,.12)" : "var(--primary-soft, rgba(13,148,136,.1))",
                  }}>
                    <Icon size={20} style={{ color: step.done ? "var(--success, #16a34a)" : "var(--primary)" }} />
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <strong style={{ fontSize: 14 }}>{step.label}</strong>
                      {!step.required && <span className="badge" style={{ fontSize: 10 }}>Optional</span>}
                    </div>
                    <p style={{ margin: "3px 0 0", fontSize: 13, color: "var(--muted)" }}>{step.desc}</p>
                  </div>
                  {step.done ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--success, #16a34a)", fontSize: 13, fontWeight: 600, flexShrink: 0 }}>
                      <CheckCircle2 size={16} /> Done
                    </span>
                  ) : (
                    <button className="btn btn-primary" style={{ flexShrink: 0 }} onClick={() => navigate(step.path)}>
                      {step.key === "test" ? "Open" : "Set up"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Footer actions */}
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="btn btn-secondary" onClick={load}>Refresh progress</button>
            <div style={{ flex: 1 }} />
            {status.completed ? (
              <button className="btn btn-primary" onClick={dismiss}>Finish</button>
            ) : (
              <button className="btn btn-secondary" onClick={dismiss}>I'll finish later</button>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
