import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Clock, Stethoscope, UserCheck, UserX } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

function waitLabel(mins) {
  if (mins === null || mins === undefined) return "";
  if (mins < 1) return "Just arrived";
  if (mins < 60) return `${mins}m waiting`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m waiting`;
}

function waitColor(mins) {
  if (!mins) return "var(--primary)";
  if (mins > 30) return "#ef4444";
  if (mins > 15) return "#f59e0b";
  return "#10b981";
}

// ── Column card ───────────────────────────────────────────────────────────────
function Column({ title, accent, icon, count, children }) {
  return (
    <div style={{
      flex: 1, minWidth: 260,
      background: "var(--surface)", border: "1px solid var(--line)",
      borderRadius: 14, overflow: "hidden", display: "flex", flexDirection: "column",
    }}>
      <div style={{
        padding: "14px 18px", borderBottom: "1px solid var(--line)",
        background: "var(--surface-2)",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <span style={{ color: accent }}>{icon}</span>
        <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, flex: 1 }}>{title}</h2>
        <span style={{
          background: accent, color: "#fff",
          borderRadius: 20, fontSize: 12, fontWeight: 800,
          padding: "2px 10px",
        }}>{count}</span>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        {children}
      </div>
    </div>
  );
}

// ── Patient card ──────────────────────────────────────────────────────────────
function PatientCard({ appt, position, onCheckIn, onCallIn, onUndo, onNoShow, onComplete, loading }) {
  const slot = new Date(appt.slot_datetime);
  const slotStr = slot.toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" });

  return (
    <div style={{
      background: "var(--surface-2)", borderRadius: 10,
      border: "1px solid var(--line)", overflow: "hidden",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px" }}>
        {/* Queue number */}
        {position !== undefined && (
          <div style={{
            width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
            background: "var(--primary)", color: "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 15, fontWeight: 800,
          }}>
            {position}
          </div>
        )}

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontWeight: 700, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {appt.patient_name}
          </p>
          <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
            Dr. {appt.doctor_name} · {slotStr}
          </p>
          {appt.patient_concern && (
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)", fontStyle: "italic" }}>
              {appt.patient_concern.slice(0, 50)}
            </p>
          )}
        </div>

        {/* Wait time */}
        {appt.wait_minutes !== null && appt.wait_minutes !== undefined && (
          <span style={{
            fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 6,
            color: waitColor(appt.wait_minutes),
            background: `${waitColor(appt.wait_minutes)}18`,
            flexShrink: 0,
          }}>
            {waitLabel(appt.wait_minutes)}
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div style={{
        display: "flex", gap: 6, padding: "8px 14px",
        borderTop: "1px solid var(--line)", background: "var(--surface)",
        flexWrap: "wrap",
      }}>
        {onCheckIn && (
          <button
            className="btn btn-primary"
            style={{ fontSize: 12, padding: "5px 12px", minHeight: "auto" }}
            onClick={() => onCheckIn(appt.id)}
            disabled={loading}
          >
            <UserCheck size={13} /> Check in
          </button>
        )}
        {onCallIn && (
          <button
            style={{
              fontSize: 12, padding: "5px 14px", minHeight: "auto",
              border: "none", borderRadius: 8, cursor: loading ? "not-allowed" : "pointer",
              display: "flex", alignItems: "center", gap: 5, fontWeight: 700,
              background: appt.doctor_is_ready ? "#0d9488" : "var(--surface-2)",
              color: appt.doctor_is_ready ? "#fff" : "var(--muted)",
              boxShadow: appt.doctor_is_ready ? "0 0 0 2px #0d9488" : "none",
              transition: "all 0.2s",
            }}
            onClick={() => onCallIn(appt.id)}
            disabled={loading}
            title={appt.doctor_is_ready ? "Doctor is ready — send patient in!" : "Waiting for doctor to signal ready"}
          >
            <Stethoscope size={13} />
            {appt.doctor_is_ready ? "Call In ✓" : "Call In"}
          </button>
        )}
        {onUndo && (
          <button
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: "5px 12px", minHeight: "auto" }}
            onClick={() => onUndo(appt.id)}
            disabled={loading}
          >
            Undo
          </button>
        )}
        {onComplete && (
          <button
            className="btn btn-primary"
            style={{ fontSize: 12, padding: "5px 12px", minHeight: "auto", background: "#10b981", borderColor: "#10b981" }}
            onClick={() => onComplete(appt.id)}
            disabled={loading}
          >
            <CheckCircle2 size={13} /> Done
          </button>
        )}
        {onNoShow && (
          <button
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: "5px 12px", minHeight: "auto" }}
            onClick={() => onNoShow(appt.id)}
            disabled={loading}
          >
            <UserX size={13} /> No show
          </button>
        )}
      </div>
    </div>
  );
}

function DoneCard({ appt }) {
  const slot = new Date(appt.slot_datetime);
  const statusColor = appt.status === "completed" ? "#10b981" : appt.status === "cancelled" ? "#ef4444" : "#f59e0b";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      padding: "10px 14px",
      background: "var(--surface-2)", borderRadius: 10,
      border: "1px solid var(--line)", opacity: 0.7,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontWeight: 600, fontSize: 13 }}>{appt.patient_name}</p>
        <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)" }}>
          Dr. {appt.doctor_name} · {slot.toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color: statusColor, textTransform: "capitalize" }}>
        {appt.status}
      </span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function WaitingRoom() {
  const [queue, setQueue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const { notify } = useToast();

  const fetchQueue = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await api.get("/appointments/queue");
      setQueue(res.data);
      setLastRefresh(new Date());
    } catch {
      if (!silent) notify("Failed to load queue.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(() => fetchQueue(true), 30000);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  const checkIn = async (id) => {
    setActionLoading(true);
    try {
      await api.post(`/appointments/${id}/checkin`);
      fetchQueue(true);
    } catch {
      notify("Failed to check in patient.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const undoCheckIn = async (id) => {
    setActionLoading(true);
    try {
      await api.post(`/appointments/${id}/checkin`);
      fetchQueue(true);
    } catch {
      notify("Failed.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const callIn = async (id) => {
    setActionLoading(true);
    try {
      await api.post(`/appointments/${id}/call-in`);
      notify("Patient sent to doctor's room.", "success");
      fetchQueue(true);
    } catch {
      notify("Failed to call in patient.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const markStatus = async (id, status) => {
    setActionLoading(true);
    try {
      await api.put(`/appointments/${id}`, { status });
      fetchQueue(true);
    } catch {
      notify("Failed to update.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const totalWaiting = queue?.waiting?.length ?? 0;
  const avgWait = totalWaiting > 0
    ? Math.round(queue.waiting.reduce((sum, a) => sum + (a.wait_minutes || 0), 0) / totalWaiting)
    : 0;
  const doctorsReady = [...(queue?.waiting ?? [])].filter((a) => a.doctor_is_ready).length;

  return (
    <AppLayout
      title="Waiting Room"
      subtitle="Track patient arrivals, queue position, and wait times in real time."
      actions={
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {lastRefresh && (
            <span style={{ fontSize: 12, color: "var(--muted)", display: "flex", alignItems: "center", gap: 4 }}>
              <Clock size={12} />
              {lastRefresh.toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          )}
          <button className="btn btn-secondary" onClick={() => fetchQueue()}>Refresh</button>
        </div>
      }
    >
      {/* Stats strip */}
      {queue && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          {[
            { label: "Expected today",   value: queue.expected.length,    color: "#6366f1" },
            { label: "In queue",         value: queue.waiting.length,     color: "#0d9488" },
            { label: "With doctor",      value: queue.with_doctor?.length ?? 0, color: "#f59e0b" },
            { label: "Doctors ready",    value: doctorsReady,             color: doctorsReady > 0 ? "#10b981" : "var(--muted)" },
            { label: "Seen today",       value: queue.done.filter((a) => a.status === "completed").length, color: "#10b981" },
          ].map((s) => (
            <div key={s.label} style={{
              flex: "1 1 140px", background: "var(--surface)", border: "1px solid var(--line)",
              borderRadius: 12, padding: "14px 18px",
            }}>
              <p style={{ margin: 0, fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</p>
              <p style={{ margin: 0, fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <SkeletonBlock className="skeleton-table" />
      ) : (
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>

          {/* Column 1: Expected */}
          <Column title="Expected" accent="#6366f1" icon={<Clock size={16} />} count={queue.expected.length}>
            {queue.expected.length === 0
              ? <p style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: "20px 0" }}>No more appointments expected today.</p>
              : queue.expected.map((a) => (
                <PatientCard
                  key={a.id} appt={a}
                  onCheckIn={checkIn}
                  onNoShow={(id) => markStatus(id, "no_show")}
                  loading={actionLoading}
                />
              ))
            }
          </Column>

          {/* Column 2: Waiting Queue */}
          <Column title="Waiting Queue" accent="#0d9488" icon={<UserCheck size={16} />} count={queue.waiting.length}>
            {queue.waiting.length === 0
              ? <p style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: "20px 0" }}>Queue is empty. Check in patients as they arrive.</p>
              : queue.waiting.map((a, i) => (
                <PatientCard
                  key={a.id} appt={a}
                  position={i + 1}
                  onCallIn={callIn}
                  onUndo={undoCheckIn}
                  onNoShow={(id) => markStatus(id, "no_show")}
                  loading={actionLoading}
                />
              ))
            }
          </Column>

          {/* Column 3: With Doctor */}
          <Column title="With Doctor" accent="#f59e0b" icon={<Stethoscope size={16} />} count={queue.with_doctor?.length ?? 0}>
            {(queue.with_doctor?.length ?? 0) === 0
              ? <p style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: "20px 0" }}>No patient with a doctor right now.</p>
              : queue.with_doctor.map((a) => (
                <PatientCard
                  key={a.id} appt={a}
                  onComplete={(id) => markStatus(id, "completed")}
                  onNoShow={(id) => markStatus(id, "no_show")}
                  loading={actionLoading}
                />
              ))
            }
          </Column>

          {/* Column 4: Done */}
          <Column title="Done Today" accent="#10b981" icon={<CheckCircle2 size={16} />} count={queue.done.length}>
            {queue.done.length === 0
              ? <p style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: "20px 0" }}>No completed appointments yet.</p>
              : queue.done.map((a) => <DoneCard key={a.id} appt={a} />)
            }
          </Column>

        </div>
      )}
    </AppLayout>
  );
}
