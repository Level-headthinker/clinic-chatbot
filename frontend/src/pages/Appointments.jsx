import { useCallback, useEffect, useState } from "react";
import { Bell, BellOff, CalendarDays, FilePlus2, List, Plus, Search, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

// ── Weekly Calendar ────────────────────────────────────────────────────────────
function WeekCalendar({ appointments }) {
  const [weekStart, setWeekStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - d.getDay() + 1); // Monday
    d.setHours(0, 0, 0, 0);
    return d;
  });

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    return d;
  });

  const apptsByDay = days.map((day) =>
    appointments.filter((a) => {
      const slot = new Date(a.slot_datetime);
      return slot.toDateString() === day.toDateString();
    })
  );

  const prevWeek = () => setWeekStart((d) => { const n = new Date(d); n.setDate(n.getDate() - 7); return n; });
  const nextWeek = () => setWeekStart((d) => { const n = new Date(d); n.setDate(n.getDate() + 7); return n; });

  const weekLabel = `${days[0].toLocaleDateString("en-PK", { day: "numeric", month: "short" })} – ${days[6].toLocaleDateString("en-PK", { day: "numeric", month: "short", year: "numeric" })}`;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <button className="btn btn-secondary" onClick={prevWeek}>←</button>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{weekLabel}</span>
        <button className="btn btn-secondary" onClick={nextWeek}>→</button>
        <button className="btn btn-secondary" onClick={() => {
          const d = new Date(); d.setDate(d.getDate() - d.getDay() + 1); d.setHours(0,0,0,0);
          setWeekStart(d);
        }}>Today</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8 }}>
        {days.map((day, i) => {
          const isToday = day.toDateString() === new Date().toDateString();
          return (
            <div key={i} style={{
              border: `1px solid ${isToday ? "var(--primary)" : "var(--line)"}`,
              borderRadius: "var(--radius-md)", overflow: "hidden", minHeight: 140,
            }}>
              <div style={{
                padding: "6px 10px",
                background: isToday ? "var(--primary)" : "var(--surface-2)",
                color: isToday ? "#fff" : "var(--text-2)",
                fontSize: 12, fontWeight: 600,
              }}>
                {day.toLocaleDateString("en-PK", { weekday: "short", day: "numeric" })}
              </div>
              <div style={{ padding: 6, display: "flex", flexDirection: "column", gap: 4 }}>
                {apptsByDay[i].length === 0
                  ? <p style={{ fontSize: 11, color: "var(--muted)", padding: "4px 2px" }}>—</p>
                  : apptsByDay[i].map((a) => (
                    <div key={a.id} style={{
                      background: `var(--${badgeColor(a.status)}-soft, var(--primary-soft))`,
                      border: `1px solid var(--${badgeColor(a.status)}-border, var(--primary-border))`,
                      borderRadius: 6, padding: "4px 7px", fontSize: 11,
                    }}>
                      <p style={{ fontWeight: 600, margin: 0 }}>{new Date(a.slot_datetime).toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })}</p>
                      <p style={{ margin: 0, color: "var(--text-2)" }}>{a.patient_name}</p>
                      <p style={{ margin: 0, color: "var(--muted)", fontSize: 10 }}>{a.doctor_name}</p>
                    </div>
                  ))
                }
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function badgeColor(status) {
  if (status === "confirmed" || status === "completed") return "success";
  if (status === "cancelled" || status === "no_show") return "danger";
  return "warning";
}

const initialVisitForm = {
  complaint: "",
  diagnosis: "",
  prescription: [],
  tests_ordered: "",
  doctor_notes: "",
  next_visit_date: "",
  fee: "",
  doctor_id: "",
};

const initialBookForm = {
  patient_name: "",
  patient_phone: "",
  patient_concern: "",
  doctor_id: "",
  slot_datetime: "",
};

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [view, setView] = useState("list"); // "list" | "calendar"
  const [visitModal, setVisitModal] = useState(null);
  const [bookModal, setBookModal] = useState(false);
  const [bookForm, setBookForm] = useState(initialBookForm);
  const [booking, setBooking] = useState(false);
  const [doctors, setDoctors] = useState([]);
  const [saving, setSaving] = useState(false);
  const [visitForm, setVisitForm] = useState(initialVisitForm);
  const [medInput, setMedInput] = useState({ medicine: "", dosage: "", frequency: "", duration: "" });
  const navigate = useNavigate();
  const { notify } = useToast();

  const fetchAppointments = useCallback(async () => {
    setLoading(true);
    try {
      const url = filter ? `/appointments/?status=${filter}` : "/appointments/";
      const res = await api.get(url);
      setAppointments(res.data);
    } catch {
      notify("Failed to load appointments.", "error");
    } finally {
      setLoading(false);
    }
  }, [filter, notify]);

  const fetchDoctors = useCallback(async () => {
    try {
      const res = await api.get("/doctors/");
      setDoctors(res.data);
    } catch {
      notify("Failed to load doctors.", "error");
    }
  }, [notify]);

  useEffect(() => {
    fetchAppointments();
    fetchDoctors();
  }, [fetchAppointments, fetchDoctors]);

  const bookAppointment = async () => {
    if (!bookForm.patient_name || !bookForm.patient_phone || !bookForm.doctor_id || !bookForm.slot_datetime) {
      notify("Please fill in all required fields.", "error");
      return;
    }
    setBooking(true);
    try {
      await api.post("/appointments/book", {
        ...bookForm,
        slot_datetime: new Date(bookForm.slot_datetime).toISOString(),
      });
      notify("Appointment booked successfully.", "success");
      setBookModal(false);
      setBookForm(initialBookForm);
      fetchAppointments();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to book appointment.", "error");
    } finally {
      setBooking(false);
    }
  };

  const filtered = appointments.filter((a) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return a.patient_name?.toLowerCase().includes(s) || a.patient_phone?.includes(s);
  });

  const updateStatus = async (id, status) => {
    try {
      await api.put(`/appointments/${id}`, { status });
      notify("Appointment status updated.", "success");
      fetchAppointments();
    } catch {
      notify("Failed to update appointment.", "error");
    }
  };

  const sendReminder = async (id) => {
    try {
      await api.post(`/appointments/${id}/remind`);
      notify("Reminder sent via WhatsApp.", "success");
      fetchAppointments();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to send reminder.", "error");
    }
  };

  const openVisitModal = (appointment) => {
    setVisitModal(appointment);
    setVisitForm({
      ...initialVisitForm,
      complaint: appointment.patient_concern || "",
      fee: appointment.doctor_fee || "",
      doctor_id: appointment.doctor_id || "",
    });
  };

  const addMedicine = () => {
    if (!medInput.medicine) return;
    setVisitForm((current) => ({
      ...current,
      prescription: [...current.prescription, { ...medInput }],
    }));
    setMedInput({ medicine: "", dosage: "", frequency: "", duration: "" });
  };

  const removeMedicine = (index) => {
    setVisitForm((current) => ({
      ...current,
      prescription: current.prescription.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const saveVisit = async () => {
    setSaving(true);
    try {
      let patientId = null;
      try {
        const lookupRes = await api.get(`/patients/lookup/${visitModal.patient_phone}`);
        patientId = lookupRes.data.id;
      } catch {
        const createRes = await api.post("/patients/", {
          name: visitModal.patient_name,
          phone: visitModal.patient_phone,
        });
        patientId = createRes.data.patient_id;
      }

      await api.post("/visits/", {
        patient_id: patientId,
        doctor_id: visitForm.doctor_id || null,
        complaint: visitForm.complaint,
        diagnosis: visitForm.diagnosis,
        prescription: visitForm.prescription,
        tests_ordered: visitForm.tests_ordered,
        doctor_notes: visitForm.doctor_notes,
        next_visit_date: visitForm.next_visit_date || null,
        fee: visitForm.fee ? parseInt(visitForm.fee) : 0,
      });

      await api.put(`/appointments/${visitModal.id}`, { status: "completed" });
      setVisitModal(null);
      notify("Visit saved and invoice created.", "success");
      fetchAppointments();
    } catch {
      notify("Failed to save visit.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout
      title="Appointments"
      subtitle="Confirm bookings, record visits, and move patients into billing."
      actions={
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", color: "var(--muted)", pointerEvents: "none" }} />
            <input
              className="input"
              placeholder="Search patient..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: 28, width: 160, fontSize: 13 }}
            />
          </div>
          <select className="select" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All status</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
            <option value="no_show">No show</option>
          </select>
          <button className="btn btn-primary" onClick={() => setBookModal(true)}>
            <Plus size={16} /> New appointment
          </button>
          <button className={`btn ${view === "list" ? "btn-primary" : "btn-secondary"}`} onClick={() => setView("list")} title="List view">
            <List size={16} />
          </button>
          <button className={`btn ${view === "calendar" ? "btn-primary" : "btn-secondary"}`} onClick={() => setView("calendar")} title="Calendar view">
            <CalendarDays size={16} />
          </button>
        </div>
      }
    >
      {view === "calendar" && !loading && (
        <div className="panel" style={{ marginBottom: 20, padding: 20 }}>
          <WeekCalendar appointments={appointments} />
        </div>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Appointment queue</h2>
          <span className="badge">{filtered.length} visible</span>
        </div>
        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={search ? "No matching appointments" : "No appointments found"}
            description={search ? "Try a different name or phone number." : "Appointments confirmed through the chatbot will appear here."}
            action={!search && <button className="btn btn-primary" onClick={() => navigate("/chat-preview")}>Test chatbot</button>}
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>{["Patient", "Phone", "Concern", "Doctor", "Slot", "Status", "Reminder", "Actions"].map((h) => <th key={h}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {filtered.map((appointment) => (
                <tr key={appointment.id}>
                  <td data-label="Patient">{appointment.patient_name}</td>
                  <td data-label="Phone">{appointment.patient_phone}</td>
                  <td data-label="Concern">{appointment.patient_concern ? `${appointment.patient_concern.slice(0, 42)}...` : "-"}</td>
                  <td data-label="Doctor">{appointment.doctor_name}</td>
                  <td data-label="Slot">{new Date(appointment.slot_datetime).toLocaleString()}</td>
                  <td data-label="Status"><span className={`badge ${badgeClass(appointment.status)}`}>{appointment.status}</span></td>
                  <td data-label="Reminder">
                    {appointment.reminder_sent
                      ? <span className="badge badge-success" title="Reminder sent"><BellOff size={13} style={{ marginRight: 4 }} />Sent</span>
                      : <button
                          className="btn btn-secondary"
                          style={{ fontSize: 12, padding: "4px 10px", minHeight: "auto" }}
                          title="Send WhatsApp reminder"
                          onClick={() => sendReminder(appointment.id)}
                          disabled={appointment.status === "cancelled" || appointment.status === "completed"}
                        >
                          <Bell size={13} /> Remind
                        </button>
                    }
                  </td>
                  <td data-label="Actions">
                    <div className="action-row" style={{ justifyContent: "flex-end" }}>
                      <select className="select" value={appointment.status} onChange={(e) => updateStatus(appointment.id, e.target.value)}>
                        <option value="pending">Pending</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="cancelled">Cancelled</option>
                        <option value="completed">Completed</option>
                        <option value="no_show">No show</option>
                      </select>
                      {appointment.status !== "cancelled" && appointment.status !== "completed" && (
                        <button className="btn btn-primary" onClick={() => openVisitModal(appointment)}>
                          <FilePlus2 size={16} />
                          Add visit
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {bookModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <h2>New appointment</h2>
                <p>Book a slot for a patient manually.</p>
              </div>
              <button className="icon-btn" onClick={() => { setBookModal(false); setBookForm(initialBookForm); }}><X size={16} /></button>
            </div>
            <div className="modal-body form-stack">
              <div className="form-grid">
                <input className="input" placeholder="Patient name *" value={bookForm.patient_name} onChange={(e) => setBookForm({ ...bookForm, patient_name: e.target.value })} />
                <input className="input" placeholder="Patient phone *" value={bookForm.patient_phone} onChange={(e) => setBookForm({ ...bookForm, patient_phone: e.target.value })} />
              </div>
              <input className="input" placeholder="Concern / reason for visit" value={bookForm.patient_concern} onChange={(e) => setBookForm({ ...bookForm, patient_concern: e.target.value })} />
              <select className="select" value={bookForm.doctor_id} onChange={(e) => setBookForm({ ...bookForm, doctor_id: e.target.value })}>
                <option value="">Select doctor *</option>
                {doctors.map((d) => <option key={d.id} value={d.id}>Dr. {d.name} — {d.specialty}</option>)}
              </select>
              <div className="field">
                <label style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 4, display: "block" }}>Appointment date & time *</label>
                <input className="input" type="datetime-local" value={bookForm.slot_datetime} onChange={(e) => setBookForm({ ...bookForm, slot_datetime: e.target.value })} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={bookAppointment} disabled={booking}>{booking ? "Booking..." : "Book appointment"}</button>
              <button className="btn btn-secondary" onClick={() => { setBookModal(false); setBookForm(initialBookForm); }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {visitModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <h2>Record visit</h2>
                <p>{visitModal.patient_name} - {visitModal.patient_phone}</p>
              </div>
              <button className="icon-btn" onClick={() => setVisitModal(null)}><X size={16} /></button>
            </div>
            <div className="modal-body form-stack">
              <div className="form-grid">
                <select className="select" value={visitForm.doctor_id} onChange={(e) => setVisitForm({ ...visitForm, doctor_id: e.target.value })}>
                  <option value="">Select doctor</option>
                  {doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>Dr. {doctor.name} - {doctor.specialty}</option>)}
                </select>
                <input className="input" type="number" placeholder="Fee PKR" value={visitForm.fee} onChange={(e) => setVisitForm({ ...visitForm, fee: e.target.value })} />
              </div>
              <textarea className="input textarea" placeholder="Complaint" value={visitForm.complaint} onChange={(e) => setVisitForm({ ...visitForm, complaint: e.target.value })} />
              <textarea className="input textarea" placeholder="Diagnosis" value={visitForm.diagnosis} onChange={(e) => setVisitForm({ ...visitForm, diagnosis: e.target.value })} />
              <div className="field">
                <label>Prescription</label>
                <div className="action-row">
                  <input className="input" placeholder="Medicine" value={medInput.medicine} onChange={(e) => setMedInput({ ...medInput, medicine: e.target.value })} />
                  <input className="input" placeholder="Dosage" value={medInput.dosage} onChange={(e) => setMedInput({ ...medInput, dosage: e.target.value })} />
                  <input className="input" placeholder="Frequency" value={medInput.frequency} onChange={(e) => setMedInput({ ...medInput, frequency: e.target.value })} />
                  <input className="input" placeholder="Duration" value={medInput.duration} onChange={(e) => setMedInput({ ...medInput, duration: e.target.value })} />
                  <button type="button" className="btn btn-secondary" onClick={addMedicine}><Plus size={16} /> Add</button>
                </div>
                <div className="chip-row">
                  {visitForm.prescription.map((medicine, index) => (
                    <span className="chip" key={`${medicine.medicine}-${index}`}>
                      {medicine.medicine} {medicine.dosage}
                      <button type="button" onClick={() => removeMedicine(index)}><X size={12} /></button>
                    </span>
                  ))}
                </div>
              </div>
              <div className="form-grid">
                <input className="input" placeholder="Tests ordered" value={visitForm.tests_ordered} onChange={(e) => setVisitForm({ ...visitForm, tests_ordered: e.target.value })} />
                <input className="input" type="date" value={visitForm.next_visit_date} onChange={(e) => setVisitForm({ ...visitForm, next_visit_date: e.target.value })} />
              </div>
              <textarea className="input textarea" placeholder="Doctor notes (private)" value={visitForm.doctor_notes} onChange={(e) => setVisitForm({ ...visitForm, doctor_notes: e.target.value })} />
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={saveVisit} disabled={saving}>{saving ? "Saving..." : "Save visit + invoice"}</button>
              <button className="btn btn-secondary" onClick={() => setVisitModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

function badgeClass(status) {
  return `badge-${badgeColor(status)}`;
}
