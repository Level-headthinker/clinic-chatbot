import { useCallback, useEffect, useState } from "react";
import {
  Check, Crown, Sparkles, Clock, CheckCircle2, XCircle, Loader2, ShieldCheck,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const PLAN_ICON = { starter: ShieldCheck, growth: Sparkles, enterprise: Crown };

export default function Subscription() {
  const [sub, setSub] = useState(null);
  const [plans, setPlans] = useState([]);
  const [trialDays, setTrialDays] = useState(3);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");        // plan key being processed
  const [pending, setPending] = useState(null); // { ref, plan } in test mode
  const { notify } = useToast();

  const load = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([
        api.get("/subscription"),
        api.get("/subscription/plans"),
      ]);
      setSub(s.data);
      setPlans(p.data.plans);
      setTrialDays(p.data.trial_days);
    } catch {
      notify("Failed to load subscription.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { load(); }, [load]);

  // Handle gateway return (?status=success|cancelled)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const st = params.get("status");
    if (st === "success") notify("Payment received — your plan is being activated.", "success");
    else if (st === "cancelled") notify("Checkout cancelled.", "info");
    if (st) window.history.replaceState({}, "", "/subscription");
  }, [notify]);

  const subscribe = async (planKey) => {
    setBusy(planKey);
    setPending(null);
    try {
      const res = await api.post("/subscription/checkout", { plan: planKey });
      if (res.data.url) {
        window.location.href = res.data.url;          // real gateway
      } else if (res.data.manual) {
        setPending({ ref: res.data.ref, plan: planKey }); // test mode
      }
    } catch (e) {
      notify(e.response?.data?.detail || "Could not start checkout.", "error");
    } finally {
      setBusy("");
    }
  };

  const confirmTest = async () => {
    setBusy("confirm");
    try {
      const res = await api.post("/subscription/manual-confirm", { ref: pending.ref });
      setSub(res.data);
      setPending(null);
      notify("Subscription activated 🎉", "success");
    } catch (e) {
      notify(e.response?.data?.detail || "Activation failed.", "error");
    } finally {
      setBusy("");
    }
  };

  const cancel = async () => {
    if (!window.confirm("Cancel your subscription? You'll keep access until the end of your current billing period.")) return;
    setBusy("cancel");
    try {
      const res = await api.post("/subscription/cancel");
      setSub(res.data);
      notify("Subscription will end at the period's close.", "success");
    } catch {
      notify("Could not cancel.", "error");
    } finally {
      setBusy("");
    }
  };

  if (loading) {
    return <AppLayout title="Subscription"><SkeletonBlock className="panel skeleton-table" /></AppLayout>;
  }

  if (!sub) {
    return (
      <AppLayout title="Subscription" subtitle="Manage your plan and billing. Cancel anytime.">
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--muted)" }}>
          <p>Couldn't load your subscription. Make sure the server is running, then reload.</p>
          <button className="btn btn-primary" onClick={() => { setLoading(true); load(); }}>Retry</button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Subscription" subtitle="Manage your plan and billing. Cancel anytime.">
      <StatusBanner sub={sub} trialDays={trialDays} onCancel={cancel} busy={busy} />

      {/* Test-mode confirm */}
      {pending && (
        <div style={testBox}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Loader2 size={18} className="spin" />
            <div>
              <strong>Test mode — simulate payment</strong>
              <p className="muted" style={{ margin: "2px 0 0", fontSize: 13 }}>
                No real gateway is configured. Click confirm to activate the <b>{pending.plan}</b> plan.
              </p>
            </div>
          </div>
          <button className="btn btn-primary" onClick={confirmTest} disabled={busy === "confirm"}>
            {busy === "confirm" ? "Activating…" : "Confirm test payment"}
          </button>
        </div>
      )}

      {/* Plan cards */}
      <div style={grid}>
        {plans.map((p) => {
          const Icon = PLAN_ICON[p.key] || ShieldCheck;
          const isCurrent = sub.plan === p.key && (sub.status === "active" || sub.status === "trialing");
          const isActivePaid = sub.plan === p.key && sub.status === "active";
          return (
            <div key={p.key} style={planCard(p.color, isCurrent)}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 38, height: 38, borderRadius: 10, background: `${p.color}1a`, color: p.color, display: "grid", placeItems: "center" }}>
                  <Icon size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0 }}>{p.label}</h3>
                  <p className="muted" style={{ margin: 0, fontSize: 12 }}>{p.tagline}</p>
                </div>
              </div>

              <div style={{ margin: "16px 0 10px" }}>
                <span style={{ fontSize: 30, fontWeight: 800 }}>₨{p.price.toLocaleString()}</span>
                <span className="muted" style={{ fontSize: 14 }}> / month</span>
              </div>

              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 18px", display: "flex", flexDirection: "column", gap: 8 }}>
                {p.highlights.map((h) => (
                  <li key={h} style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 13 }}>
                    <Check size={16} style={{ color: p.color, flexShrink: 0, marginTop: 1 }} /> {h}
                  </li>
                ))}
              </ul>

              {isActivePaid ? (
                <button className="btn btn-secondary" disabled style={{ width: "100%", justifyContent: "center" }}>
                  <CheckCircle2 size={16} /> Current plan
                </button>
              ) : (
                <button
                  className="btn btn-primary"
                  style={{ width: "100%", justifyContent: "center", background: p.color, borderColor: p.color }}
                  onClick={() => subscribe(p.key)}
                  disabled={!!busy}
                >
                  {busy === p.key ? "Starting…" : isCurrent ? "Subscribe (end trial)" : "Choose plan"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <p className="muted" style={{ textAlign: "center", fontSize: 12, marginTop: 18, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
        <ShieldCheck size={14} /> Secure checkout · Cancel anytime · {trialDays}-day free trial on signup
      </p>

      <style>{`.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </AppLayout>
  );
}

function StatusBanner({ sub, trialDays, onCancel, busy }) {
  const map = {
    trialing: {
      icon: Clock, color: "#2563eb", bg: "rgba(37,99,235,.08)",
      title: `Free trial — ${sub.days_left} day${sub.days_left === 1 ? "" : "s"} left`,
      text: `You're on the ${sub.plan_label} plan trial. Subscribe before it ends to keep your bot running.`,
    },
    active: {
      icon: CheckCircle2, color: "#16a34a", bg: "rgba(22,163,74,.08)",
      title: `${sub.plan_label} plan — active`,
      text: sub.cancel_at_period_end
        ? `Cancels on ${fmt(sub.current_period_end)}. You keep access until then.`
        : `Renews on ${fmt(sub.current_period_end)}.`,
    },
    cancelled: {
      icon: XCircle, color: "#d97706", bg: "rgba(217,119,6,.08)",
      title: "Subscription cancelled",
      text: `You still have access until ${fmt(sub.current_period_end)}.`,
    },
    past_due: {
      icon: XCircle, color: "#dc2626", bg: "rgba(220,38,38,.08)",
      title: "Payment failed",
      text: "Please update your payment to keep your service running.",
    },
    expired: {
      icon: XCircle, color: "#dc2626", bg: "rgba(220,38,38,.08)",
      title: "Trial / subscription ended",
      text: "Choose a plan below to reactivate your clinic bot.",
    },
  };
  const s = map[sub.status] || map.expired;
  const Icon = s.icon;
  const canCancel = sub.status === "active" && !sub.cancel_at_period_end;
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
      padding: "16px 20px", borderRadius: 12, marginBottom: 20,
      background: s.bg, border: `1px solid ${s.color}33`, flexWrap: "wrap",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Icon size={24} style={{ color: s.color, flexShrink: 0 }} />
        <div>
          <strong style={{ color: s.color }}>{s.title}</strong>
          <p style={{ margin: "2px 0 0", fontSize: 13, color: "var(--text-2, var(--muted))" }}>{s.text}</p>
        </div>
      </div>
      {canCancel && (
        <button className="btn btn-secondary" onClick={onCancel} disabled={busy === "cancel"}>
          {busy === "cancel" ? "Cancelling…" : "Cancel subscription"}
        </button>
      )}
    </div>
  );
}

function fmt(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-PK", { day: "2-digit", month: "short", year: "numeric" });
}

const grid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 };
const planCard = (color, current) => ({
  background: "var(--surface)", borderRadius: 14, padding: 22,
  border: `2px solid ${current ? color : "var(--line)"}`,
  boxShadow: current ? `0 4px 20px ${color}22` : "none",
  position: "relative", display: "flex", flexDirection: "column",
});
const testBox = {
  display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
  padding: "14px 18px", borderRadius: 12, marginBottom: 20, flexWrap: "wrap",
  background: "rgba(13,148,136,.08)", border: "1px dashed var(--accent, #0d9488)",
};
