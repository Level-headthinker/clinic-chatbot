import { useCallback, useEffect, useState } from "react";
import { Calendar, ClipboardList, LogOut, Moon, Save, Sun, Users, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { SkeletonBlock } from "../components/Skeleton";

const TABS = [
  { key: "schedule",     label: "My Schedule",   icon: Calendar },
  { key: "patients",     label: "My Patients",   icon: Users },
  { key: "profile",      label: "Profile",       icon: ClipboardList },
];

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function statusBadge(s) {
  if (s === "confirmed" || s === "completed") return { bg: "#d1fae5", color: "#065f46", label: s };
  if (s === "cancelled" || s === "no_show")  return { bg: "#fee2e2", color: "#991b1b", label: s };
  return { bg: "#fef3c7", color: "#92400e", label: s };
}

export default function DoctorPortal() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [tab, setTab] = useState("schedule");
  const [doctor, setDoctor] = useState(null);
  const [stats, setStats] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [patients, setPatients] = useState(null);
  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("theme") === "dark");

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [meRes, statsRes, schedRes] = await Promise.all([
        api.get("/doctor/me"),
        api.get("/doctor/stats"),
        api.get("/doctor/schedule"),
      ]);
      setDoctor(meRes.data);
      setStats(statsRes.data);
      setSchedule(schedRes.data);
    } catch {
      notify("Failed to load portal data.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  const loadPatients = useCallback(async () => {
    if (patients) return;
    try {
      const res = await api.get("/doctor/patients");
      setPatients(res.data);
    } catch {
      notify("Failed to load patients.", "error");
    }
  }, [patients, notify]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (tab === "patients") loadPatients();
  }, [tab, loadPatients]);

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      {/* Top header */}
      <header style={{
        background: "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
        padding: "0 24px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: 60, flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: "50%",
            background: "rgba(255,255,255,0.2)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16, fontWeight: 700, color: "#fff",
          }}>
            {doctor?.name?.[0]?.toUpperCase() || "D"}
          </div>
          <div>
            <p style={{ color: "#fff", fontWeight: 700, margin: 0, fontSize: 15 }}>
              Dr. {doctor?.name || user?.user_name || "Doctor"}
            </p>
            <p style={{ color: "rgba(255,255,255,0.75)", margin: 0, fontSize: 12 }}>
              {doctor?.specialty || ""}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            onClick={() => setDarkMode((d) => !d)}
            style={{ background: "rgba(255,255,255,0.15)", border: "none", borderRadius: 8, padding: "6px 10px", cursor: "pointer", color: "#fff", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
          >
            {darkMode ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          <button
            onClick={handleLogout}
            style={{ background: "rgba(255,255,255,0.15)", border: "none", borderRadius: 8, padding: "6px 12px", cursor: "pointer", color: "#fff", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
          >
            <LogOut size={15} /> Logout
          </button>
        </div>
      </header>

      {/* Stats strip */}
      {stats && (
        <div style={{
          display: "flex", gap: 0,
          background: "var(--surface)", borderBottom: "1px solid var(--line)",
        }}>
          {[
            { label: "Today", value: stats.today_appointments },
            { label: "Total Appointments", value: stats.total_appointments },
            { label: "Total Visits", value: stats.total_visits },
            { label: "Patients Seen", value: stats.total_patients },
          ].map((s, i) => (
            <div key={i} style={{
              flex: 1, padding: "14px 20px", textAlign: "center",
              borderRight: i < 3 ? "1px solid var(--line)" : "none",
            }}>
              <p style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--primary)" }}>{s.value}</p>
              <p style={{ margin: 0, fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: "flex", background: "var(--surface)", borderBottom: "1px solid var(--line)", padding: "0 16px" }}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "12px 18px", border: "none", background: "none", cursor: "pointer",
              fontSize: 13, fontWeight: tab === key ? 700 : 500,
              color: tab === key ? "var(--primary)" : "var(--text-2)",
              borderBottom: tab === key ? "2px solid var(--primary)" : "2px solid transparent",
              marginBottom: -1,
            }}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: 24, maxWidth: 900, width: "100%", margin: "0 auto" }}>
        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : (
          <>
            {tab === "schedule" && <ScheduleTab schedule={schedule} onNotesUpdated={load} />}
            {tab === "patients" && <PatientsTab patients={patients} />}
            {tab === "profile"  && <ProfileTab doctor={doctor} onAvailabilityUpdated={load} />}
          </>
        )}
      </div>
    </div>
  );
}

// ── Schedule tab ──────────────────────────────────────────────────────────────
function ScheduleTab({ schedule, onNotesUpdated }) {
  if (!schedule) return null;
  const { today, upcoming } = schedule;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <Section title="Today's Appointments" count={today.length} accent="#0d9488">
        {today.length === 0
          ? <Empty text="No appointments scheduled for today." />
          : today.map((a) => <ApptRow key={a.id} appt={a} highlight onNotesUpdated={onNotesUpdated} />)
        }
      </Section>

      <Section title="Upcoming (next 7 days)" count={upcoming.length} accent="#6366f1">
        {upcoming.length === 0
          ? <Empty text="No upcoming appointments this week." />
          : upcoming.map((a) => <ApptRow key={a.id} appt={a} onNotesUpdated={onNotesUpdated} />)
        }
      </Section>
    </div>
  );
}

function ApptRow({ appt, highlight, onNotesUpdated }) {
  const { notify } = useToast();
  const badge = statusBadge(appt.status);
  const dt = appt.slot_datetime ? new Date(appt.slot_datetime) : null;
  const [expanded, setExpanded] = useState(false);
  const [notes, setNotes] = useState(appt.notes || "");
  const [saving, setSaving] = useState(false);

  const saveNotes = async () => {
    setSaving(true);
    try {
      await api.patch(`/doctor/appointments/${appt.id}/notes`, { notes });
      notify("Notes saved.", "success");
      if (onNotesUpdated) onNotesUpdated();
    } catch {
      notify("Failed to save notes.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      background: highlight ? "rgba(13,148,136,0.05)" : "var(--surface-2)",
      borderRadius: 10, marginBottom: 8,
      borderLeft: highlight ? "3px solid #0d9488" : "3px solid transparent",
      overflow: "hidden",
    }}>
      <div
        style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 16px", cursor: "pointer" }}
        onClick={() => setExpanded((e) => !e)}
      >
        <div style={{ minWidth: 52, textAlign: "center" }}>
          <p style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--primary)" }}>
            {dt ? dt.toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" }) : "—"}
          </p>
          {!highlight && dt && (
            <p style={{ margin: 0, fontSize: 10, color: "var(--muted)" }}>
              {dt.toLocaleDateString("en-PK", { weekday: "short", month: "short", day: "numeric" })}
            </p>
          )}
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>{appt.patient_name}</p>
          <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
            {appt.patient_phone}{appt.patient_concern ? ` · ${appt.patient_concern.slice(0, 50)}` : ""}
          </p>
          {notes && !expanded && (
            <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--primary)", fontStyle: "italic" }}>
              📝 {notes.slice(0, 60)}{notes.length > 60 ? "…" : ""}
            </p>
          )}
        </div>
        <span style={{ background: badge.bg, color: badge.color, borderRadius: 6, fontSize: 11, fontWeight: 700, padding: "3px 9px" }}>
          {badge.label}
        </span>
        <span style={{ fontSize: 11, color: "var(--muted)", userSelect: "none" }}>{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div style={{ padding: "0 16px 14px", borderTop: "1px solid var(--line)" }}>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "10px 0 6px", fontWeight: 600 }}>CLINICAL NOTES</p>
          <textarea
            style={{
              width: "100%", minHeight: 90, padding: "8px 10px",
              border: "1px solid var(--line)", borderRadius: 8,
              background: "var(--surface)", color: "var(--text)",
              fontSize: 13, resize: "vertical", fontFamily: "inherit", boxSizing: "border-box",
            }}
            placeholder="Write clinical notes, diagnosis, follow-up instructions…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
            <button
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "var(--primary)", color: "#fff", border: "none",
                borderRadius: 8, padding: "7px 16px", fontSize: 13, cursor: "pointer",
                opacity: saving ? 0.7 : 1,
              }}
              onClick={saveNotes}
              disabled={saving}
            >
              <Save size={14} /> {saving ? "Saving…" : "Save notes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Patients tab ──────────────────────────────────────────────────────────────
function PatientsTab({ patients }) {
  if (!patients) return <SkeletonBlock className="skeleton-table" />;
  return (
    <Section title="Patients Seen" count={patients.length} accent="#6366f1">
      {patients.length === 0
        ? <Empty text="No patients recorded yet. Patients appear here after a visit is logged." />
        : patients.map((p) => (
          <div key={p.id} style={{
            display: "flex", alignItems: "center", gap: 14,
            padding: "11px 16px",
            background: "var(--surface-2)", borderRadius: 10, marginBottom: 8,
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%",
              background: "var(--primary-soft)", color: "var(--primary)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontWeight: 700, fontSize: 15, flexShrink: 0,
            }}>
              {p.name?.[0]?.toUpperCase() || "P"}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>{p.name}</p>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                {p.phone}
                {p.diagnosis ? ` · ${p.diagnosis.slice(0, 50)}` : ""}
              </p>
            </div>
            {p.last_visit && (
              <span style={{ fontSize: 11, color: "var(--muted)", flexShrink: 0 }}>
                {new Date(p.last_visit).toLocaleDateString()}
              </span>
            )}
          </div>
        ))
      }
    </Section>
  );
}

// ── Profile tab ───────────────────────────────────────────────────────────────
function ProfileTab({ doctor, onAvailabilityUpdated }) {
  const { notify } = useToast();
  const [timings, setTimings] = useState(doctor?.timings || []);
  const [timingInput, setTimingInput] = useState({ day: "Monday", from: "09:00 AM", to: "05:00 PM" });
  const [saving, setSaving] = useState(false);

  if (!doctor) return null;

  const addTiming = () => {
    if (timings.some((t) => t.day === timingInput.day)) {
      setTimings((prev) => prev.map((t) => t.day === timingInput.day ? { ...timingInput } : t));
    } else {
      setTimings((prev) => [...prev, { ...timingInput }]);
    }
  };

  const removeTiming = (day) => setTimings((prev) => prev.filter((t) => t.day !== day));

  const saveAvailability = async () => {
    setSaving(true);
    try {
      await api.put("/doctor/availability", { timings });
      notify("Availability updated.", "success");
      if (onAvailabilityUpdated) onAvailabilityUpdated();
    } catch {
      notify("Failed to save availability.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Section title="My Profile" accent="#0d9488">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
          <InfoCard label="Name" value={`Dr. ${doctor.name}`} />
          <InfoCard label="Specialty" value={doctor.specialty} />
          <InfoCard label="Qualification" value={doctor.qualification || "—"} />
          <InfoCard label="Fee" value={doctor.fee || "—"} />
        </div>
        {doctor.bio && (
          <div style={{ marginTop: 16, padding: 16, background: "var(--surface-2)", borderRadius: 10 }}>
            <p style={{ margin: 0, fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>BIO</p>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{doctor.bio}</p>
          </div>
        )}
      </Section>

      <Section title="My Availability" accent="#6366f1">
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 14 }}>
          Set the days and hours you are available. The chatbot uses this to show patients when they can book.
        </p>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12, alignItems: "center" }}>
          <select
            style={{ padding: "7px 10px", border: "1px solid var(--line)", borderRadius: 8, background: "var(--surface)", color: "var(--text)", fontSize: 13 }}
            value={timingInput.day}
            onChange={(e) => setTimingInput({ ...timingInput, day: e.target.value })}
          >
            {DAYS.map((d) => <option key={d}>{d}</option>)}
          </select>
          <input
            style={{ padding: "7px 10px", border: "1px solid var(--line)", borderRadius: 8, background: "var(--surface)", color: "var(--text)", fontSize: 13, width: 110 }}
            placeholder="From e.g. 9:00 AM"
            value={timingInput.from}
            onChange={(e) => setTimingInput({ ...timingInput, from: e.target.value })}
          />
          <input
            style={{ padding: "7px 10px", border: "1px solid var(--line)", borderRadius: 8, background: "var(--surface)", color: "var(--text)", fontSize: 13, width: 110 }}
            placeholder="To e.g. 5:00 PM"
            value={timingInput.to}
            onChange={(e) => setTimingInput({ ...timingInput, to: e.target.value })}
          />
          <button
            style={{ padding: "7px 14px", background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 8, cursor: "pointer", fontSize: 13, color: "var(--text)" }}
            type="button" onClick={addTiming}
          >
            Add day
          </button>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {timings.length === 0
            ? <p style={{ fontSize: 13, color: "var(--muted)" }}>No days added yet.</p>
            : timings.map((t) => (
              <span key={t.day} style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "var(--primary-soft)", color: "var(--primary)",
                borderRadius: 8, padding: "5px 12px", fontSize: 12, fontWeight: 600,
              }}>
                {t.day} · {t.from} – {t.to}
                <button
                  type="button"
                  onClick={() => removeTiming(t.day)}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0, color: "var(--primary)", display: "flex" }}
                >
                  <X size={12} />
                </button>
              </span>
            ))
          }
        </div>

        <button
          style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "var(--primary)", color: "#fff", border: "none",
            borderRadius: 8, padding: "8px 18px", fontSize: 13, cursor: "pointer",
            opacity: saving ? 0.7 : 1,
          }}
          onClick={saveAvailability}
          disabled={saving}
        >
          <Save size={14} /> {saving ? "Saving…" : "Save availability"}
        </button>
      </Section>
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────
function Section({ title, count, accent, children }) {
  return (
    <div style={{ background: "var(--surface)", borderRadius: 12, border: "1px solid var(--line)", overflow: "hidden" }}>
      <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 4, height: 18, borderRadius: 2, background: accent, display: "inline-block" }} />
        <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{title}</h2>
        {count !== undefined && (
          <span style={{ background: accent, color: "#fff", borderRadius: 10, fontSize: 11, fontWeight: 700, padding: "2px 8px", marginLeft: "auto" }}>
            {count}
          </span>
        )}
      </div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  );
}

function Empty({ text }) {
  return <p style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: "20px 0", margin: 0 }}>{text}</p>;
}

function InfoCard({ label, value }) {
  return (
    <div style={{ background: "var(--surface-2)", borderRadius: 10, padding: "12px 16px" }}>
      <p style={{ margin: 0, fontSize: 11, color: "var(--muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
      <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>{value}</p>
    </div>
  );
}
