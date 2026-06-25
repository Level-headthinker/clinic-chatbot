import { Menu } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api/axios";
import Sidebar from "./Sidebar";

// The bell surfaces operational alerts (today's appointments, new leads, due
// follow-ups). It only belongs on the day-to-day operational pages — not on
// content/config pages like Knowledge Base, Analytics, Conversations, Settings.
const BELL_PATHS = [
  "/dashboard", "/appointments", "/patients", "/leads",
  "/follow-ups", "/waiting-room", "/billing", "/doctors", "/services",
];

function shouldShowBell(pathname) {
  return BELL_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

// Inject keyframe animations once
(function injectStyles() {
  if (document.getElementById("clinic-bell-css")) return;
  const s = document.createElement("style");
  s.id = "clinic-bell-css";
  s.textContent = `
    @keyframes bellSwing {
      0%,100% { transform-origin: top center; transform: rotate(0deg); }
      15%      { transform: rotate(10deg); }
      45%      { transform: rotate(-8deg); }
      65%      { transform: rotate(6deg); }
      85%      { transform: rotate(-4deg); }
    }
    @keyframes pulseRing {
      0%   { transform: scale(1);   opacity: 0.7; }
      100% { transform: scale(2.4); opacity: 0; }
    }
    @keyframes notifFadeIn {
      from { opacity: 0; transform: translateY(-6px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0)   scale(1);    }
    }
    @keyframes liveDot {
      0%,100% { opacity: 1; }
      50%      { opacity: 0.3; }
    }
    .bell-swing { animation: bellSwing 0.9s ease both; }
  `;
  document.head.appendChild(s);
})();

// ── Custom clinic bell SVG (bell body + ECG heartbeat line) ───────────────────
function ClinicBellSVG({ active }) {
  return (
    <svg
      width="22" height="22" viewBox="0 0 24 24"
      fill="none" xmlns="http://www.w3.org/2000/svg"
      style={{
        filter: active
          ? "drop-shadow(0 0 4px rgba(13,148,136,0.55))"
          : "none",
        transition: "filter 0.3s",
      }}
    >
      {/* Crown/hook */}
      <line x1="12" y1="1" x2="12" y2="3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {/* Bell dome */}
      <path
        d="M12 3.5C7.86 3.5 4.5 6.86 4.5 11v4h15v-4C19.5 6.86 16.14 3.5 12 3.5z"
        stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"
      />
      {/* Bell rim */}
      <path d="M3 15h18" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      {/* Clapper */}
      <path d="M9.5 15a2.5 2.5 0 0 0 5 0" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      {/* ECG / heartbeat line across bell body — the clinic signature */}
      <path
        d="M6 10.5h2.2l1.1-2.5 1.6 5.2 1.1-3.2.5.5H18"
        stroke="currentColor" strokeWidth="1.25"
        strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}

// ── Two-track pill badge ───────────────────────────────────────────────────────
function TrackBadge({ count, color, side }) {
  if (!count) return null;
  return (
    <span style={{
      position: "absolute",
      top: -6,
      [side]: -8,
      background: color,
      color: "#fff",
      borderRadius: 10,
      fontSize: 10,
      fontWeight: 800,
      minWidth: 18,
      height: 18,
      padding: "0 4px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      lineHeight: 1,
      pointerEvents: "none",
      border: "2px solid var(--surface)",
      letterSpacing: "-0.5px",
    }}>
      {count > 99 ? "99+" : count}
    </span>
  );
}

// ── Dropdown row ──────────────────────────────────────────────────────────────
function NotifRow({ icon, label, sub, accent, overdue }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "9px 16px",
      borderLeft: `3px solid ${accent}`,
      marginBottom: 1,
      background: "var(--surface-2)",
    }}>
      <span style={{
        fontSize: 16, lineHeight: 1, marginTop: 1, minWidth: 20, textAlign: "center",
      }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "var(--text-1)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {label}
        </p>
        {sub && (
          <p style={{ margin: "2px 0 0", fontSize: 11, color: overdue ? "#ef4444" : "var(--muted)" }}>
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────────────────
function SectionHeader({ label, count, color, emoji }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 16px 6px",
      background: "var(--surface)",
    }}>
      <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color }}>
        <span>{emoji}</span> {label}
      </span>
      <span style={{
        background: color, color: "#fff",
        borderRadius: 10, fontSize: 10, fontWeight: 800,
        padding: "1px 7px",
      }}>{count}</span>
    </div>
  );
}

// ── Section action link ───────────────────────────────────────────────────────
function SectionAction({ label, onClick }) {
  return (
    <button onClick={onClick} style={{
      display: "block", width: "100%", textAlign: "right",
      padding: "5px 16px 10px", fontSize: 11, color: "var(--primary)",
      background: "none", border: "none", cursor: "pointer", fontWeight: 700,
      borderBottom: "1px solid var(--line)",
    }}>
      {label} →
    </button>
  );
}

// ── Main notification bell ────────────────────────────────────────────────────
function NotificationBell() {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [swinging, setSwinging] = useState(false);
  const prevTotal = useRef(0);
  const ref = useRef(null);
  const navigate = useNavigate();

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await api.get("/notifications/");
      setData(res.data);
      const newTotal = res.data?.total ?? 0;
      if (newTotal > prevTotal.current) {
        setSwinging(true);
        setTimeout(() => setSwinging(false), 1000);
      }
      prevTotal.current = newTotal;
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const apptCount = data?.today_appointments?.length ?? 0;
  const leadCount = data?.new_leads?.length ?? 0;
  const fuCount   = data?.due_followups?.length ?? 0;
  const hasAny    = apptCount + leadCount + fuCount > 0;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      {/* Pulse ring behind button when active */}
      {hasAny && !open && (
        <span style={{
          position: "absolute", inset: 0, borderRadius: "50%",
          background: "rgba(13,148,136,0.25)",
          animation: "pulseRing 1.8s ease-out infinite",
          pointerEvents: "none",
        }} />
      )}

      <button
        className={`icon-btn ${swinging ? "bell-swing" : ""}`}
        onClick={() => setOpen((o) => !o)}
        title="Clinic alerts"
        style={{ position: "relative", zIndex: 1 }}
      >
        <ClinicBellSVG active={hasAny} />

        {/* Appointments badge — teal, left */}
        <TrackBadge count={apptCount} color="#0d9488" side="left" />

        {/* Leads badge — amber, right */}
        <TrackBadge count={leadCount} color="#d97706" side="right" />
      </button>

      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 10px)", right: 0,
          width: 300, maxHeight: 500, overflowY: "auto",
          background: "var(--surface)", border: "1px solid var(--line)",
          borderRadius: 12, boxShadow: "0 8px 32px rgba(0,0,0,0.14)",
          zIndex: 200,
          animation: "notifFadeIn 0.18s ease both",
        }}>
          {/* Dropdown header */}
          <div style={{
            padding: "12px 16px",
            background: "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
            borderRadius: "12px 12px 0 0",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ClinicBellSVG active={false} />
              <span style={{ color: "#fff", fontWeight: 700, fontSize: 14 }}>Clinic Alerts</span>
            </div>
            {hasAny && (
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%", background: "#fff",
                  animation: "liveDot 1.2s ease infinite",
                }} />
                <span style={{ color: "rgba(255,255,255,0.85)", fontSize: 11, fontWeight: 600 }}>Live</span>
              </div>
            )}
          </div>

          {!hasAny ? (
            <div style={{ padding: "28px 16px", textAlign: "center" }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>✅</div>
              <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>All caught up — no alerts right now</p>
            </div>
          ) : (
            <>
              {/* Appointments section */}
              {apptCount > 0 && (
                <div>
                  <SectionHeader label="Today's Appointments" count={apptCount} color="#0d9488" emoji="📅" />
                  {data.today_appointments.map((a) => (
                    <NotifRow
                      key={a.id}
                      icon="🕐"
                      label={a.patient_name}
                      sub={`${new Date(a.slot_datetime).toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })} · Dr. ${a.doctor_name}`}
                      accent="#0d9488"
                    />
                  ))}
                  <SectionAction label="Open appointments" onClick={() => { navigate("/appointments"); setOpen(false); }} />
                </div>
              )}

              {/* Leads section */}
              {leadCount > 0 && (
                <div>
                  <SectionHeader label="New Leads" count={leadCount} color="#d97706" emoji="👤" />
                  {data.new_leads.map((l) => (
                    <NotifRow
                      key={l.id}
                      icon="📞"
                      label={l.name}
                      sub={l.phone}
                      accent="#d97706"
                    />
                  ))}
                  <SectionAction label="Open leads" onClick={() => { navigate("/leads"); setOpen(false); }} />
                </div>
              )}

              {/* Follow-ups section */}
              {fuCount > 0 && (
                <div>
                  <SectionHeader label="Follow-ups Due" count={fuCount} color="#ef4444" emoji="⚠️" />
                  {data.due_followups.map((f) => (
                    <NotifRow
                      key={f.id}
                      icon={f.overdue ? "🔴" : "🟡"}
                      label={f.title}
                      sub={f.overdue ? "Overdue" : "Due today"}
                      accent="#ef4444"
                      overdue={f.overdue}
                    />
                  ))}
                  <SectionAction label="Open follow-ups" onClick={() => { navigate("/follow-ups"); setOpen(false); }} />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── AppLayout ─────────────────────────────────────────────────────────────────
export default function AppLayout({ title, subtitle, actions, children, showBell }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { pathname } = useLocation();
  // Explicit prop wins; otherwise decide by route.
  const bellVisible = showBell ?? shouldShowBell(pathname);

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {sidebarOpen && (
        <button
          className="sidebar-scrim"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        />
      )}
      <main className="app-main">
        <header className="page-header">
          <div className="page-title-row">
            <button
              className="icon-btn mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1>{title}</h1>
              {subtitle && <p>{subtitle}</p>}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {bellVisible && <NotificationBell />}
            {actions && <div className="page-actions">{actions}</div>}
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
