import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Clock, DoorOpen, Search, Stethoscope, UserCheck, UserPlus, UserX, X } from "lucide-react";
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
            {appt.room_name && <span> · <DoorOpen size={11} style={{ verticalAlign: "middle" }} /> {appt.room_name}</span>}
          </p>
          {(appt.service_name || appt.patient_concern) && (
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)", fontStyle: "italic" }}>
              {(appt.service_name || appt.patient_concern || "").slice(0, 60)}
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

// ── Walk-in modal ─────────────────────────────────────────────────────────────
function WalkInModal({ onClose, onSave }) {
  const [step, setStep] = useState(1); // 1=patient info, 2=service lookup, 3=assign
  const [form, setForm] = useState({ name: "", phone: "", service: "" });
  const [options, setOptions] = useState(null); // { doctors, rooms }
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [saving, setSaving] = useState(false);
  const [searching, setSearching] = useState(false);
  const { notify } = useToast();

  const searchService = async () => {
    if (!form.service.trim()) return;
    setSearching(true);
    try {
      const res = await api.get(`/appointments/available-for/${encodeURIComponent(form.service.trim())}`);
      setOptions(res.data);
      setStep(3);
    } catch {
      notify("Failed to search. Try again.", "error");
    } finally {
      setSearching(false);
    }
  };

  const submit = async () => {
    if (!selectedDoctor) { notify("Please select a doctor.", "error"); return; }
    setSaving(true);
    try {
      await api.post("/appointments/walk-in", {
        patient_name: form.name.trim(),
        patient_phone: form.phone.trim(),
        patient_concern: form.service.trim(),
        service_name: form.service.trim(),
        doctor_id: selectedDoctor.id,
        room_id: selectedRoom?.id || null,
      });
      notify("Walk-in patient assigned!", "success");
      onSave();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to assign walk-in.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: "var(--surface)", borderRadius: 18, padding: 28,
        width: 480, maxHeight: "90vh", overflowY: "auto",
        boxShadow: "0 24px 80px rgba(0,0,0,0.35)",
      }} onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18 }}>Walk-in Patient</h2>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
              {step === 1 ? "Step 1: Patient info" : step === 2 ? "Step 2: Requested service" : "Step 3: Assign staff & room"}
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)" }}>
            <X size={20} />
          </button>
        </div>

        {/* Step 1: Patient info */}
        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Patient Name *</label>
              <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" />
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Phone</label>
              <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="03xx-xxxxxxx" />
            </div>
            <button
              className="btn btn-primary"
              style={{ marginTop: 4 }}
              disabled={!form.name.trim()}
              onClick={() => setStep(2)}
            >
              Next: Select Service
            </button>
          </div>
        )}

        {/* Step 2: Service search */}
        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>What service does the patient want? *</label>
              <input
                className="input"
                value={form.service}
                onChange={(e) => setForm({ ...form, service: e.target.value })}
                placeholder="e.g. Hydra Facial, Laser Hair Removal"
                onKeyDown={(e) => e.key === "Enter" && searchService()}
                autoFocus
              />
              <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--muted)" }}>
                The system will find doctors who can perform this and available rooms.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>Back</button>
              <button
                className="btn btn-primary"
                style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                disabled={!form.service.trim() || searching}
                onClick={searchService}
              >
                <Search size={14} /> {searching ? "Searching…" : "Find Available Staff"}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Select doctor + room */}
        {step === 3 && options && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Doctors */}
            <div>
              <p style={{ margin: "0 0 8px", fontWeight: 700, fontSize: 13 }}>
                Doctors who can do "{options.service}" ({options.doctors.length})
              </p>
              {options.doctors.length === 0 ? (
                <div style={{ padding: "14px", background: "var(--surface-2)", borderRadius: 10, color: "var(--muted)", fontSize: 13, textAlign: "center" }}>
                  No doctors available for this service right now.
                  <br />
                  <span style={{ fontSize: 11 }}>Check that doctors have this service listed in their treatments.</span>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {options.doctors.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => !d.is_busy && setSelectedDoctor(d)}
                      style={{
                        padding: "12px 14px", borderRadius: 10, border: "2px solid",
                        borderColor: selectedDoctor?.id === d.id ? "var(--primary)" : "var(--line)",
                        background: d.is_busy ? "var(--surface-2)" : selectedDoctor?.id === d.id ? "var(--primary-light, #f0fdf4)" : "var(--surface-2)",
                        cursor: d.is_busy ? "not-allowed" : "pointer",
                        opacity: d.is_busy ? 0.55 : 1,
                        display: "flex", alignItems: "center", gap: 12, textAlign: "left",
                      }}
                    >
                      <Stethoscope size={16} color={selectedDoctor?.id === d.id ? "var(--primary)" : "var(--muted)"} />
                      <div style={{ flex: 1 }}>
                        <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>Dr. {d.name}</p>
                        <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>{d.specialty}</p>
                      </div>
                      {d.is_busy ? (
                        <span style={{ fontSize: 11, color: "#ef4444", fontWeight: 700 }}>Busy</span>
                      ) : d.is_ready ? (
                        <span style={{ fontSize: 11, color: "#10b981", fontWeight: 700 }}>Ready</span>
                      ) : null}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Rooms */}
            <div>
              <p style={{ margin: "0 0 8px", fontWeight: 700, fontSize: 13 }}>
                Available Rooms ({options.rooms.length}) <span style={{ fontWeight: 400, color: "var(--muted)" }}>— optional</span>
              </p>
              {options.rooms.length === 0 ? (
                <div style={{ padding: "10px 14px", background: "var(--surface-2)", borderRadius: 10, color: "var(--muted)", fontSize: 13 }}>
                  No free rooms. You can still assign without a room.
                </div>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  <button
                    onClick={() => setSelectedRoom(null)}
                    style={{
                      padding: "8px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                      border: "2px solid", borderColor: !selectedRoom ? "var(--primary)" : "var(--line)",
                      background: !selectedRoom ? "var(--primary)" : "var(--surface-2)",
                      color: !selectedRoom ? "#fff" : "var(--text)",
                      cursor: "pointer",
                    }}
                  >
                    No room
                  </button>
                  {options.rooms.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => setSelectedRoom(r)}
                      style={{
                        padding: "8px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                        border: "2px solid", borderColor: selectedRoom?.id === r.id ? "var(--primary)" : "var(--line)",
                        background: selectedRoom?.id === r.id ? "var(--primary)" : "var(--surface-2)",
                        color: selectedRoom?.id === r.id ? "#fff" : "var(--text)",
                        cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
                      }}
                    >
                      <DoorOpen size={13} /> {r.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
              <button className="btn btn-secondary" onClick={() => setStep(2)}>Back</button>
              <button
                className="btn btn-primary"
                style={{ flex: 1 }}
                disabled={!selectedDoctor || saving}
                onClick={submit}
              >
                {saving ? "Assigning…" : "Assign & Send to Room"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function WaitingRoom() {
  const [queue, setQueue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [showWalkIn, setShowWalkIn] = useState(false);
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
          <button
            className="btn btn-primary"
            style={{ display: "flex", alignItems: "center", gap: 6 }}
            onClick={() => setShowWalkIn(true)}
          >
            <UserPlus size={15} /> Walk-in
          </button>
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

      {showWalkIn && (
        <WalkInModal
          onClose={() => setShowWalkIn(false)}
          onSave={() => { setShowWalkIn(false); fetchQueue(true); }}
        />
      )}
    </AppLayout>
  );
}
