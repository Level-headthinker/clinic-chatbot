import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, MessageSquare, Plus, Trash2, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const initialVisitForm = {
  complaint: "",
  diagnosis: "",
  tests_ordered: "",
  test_results: "",
  doctor_notes: "",
  next_visit_date: "",
  fee: "",
  doctor_id: "",
  prescription: [],
};

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showVisitForm, setShowVisitForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [visitForm, setVisitForm] = useState(initialVisitForm);
  const [medInput, setMedInput] = useState({ medicine: "", dosage: "", frequency: "", duration: "", notes: "" });

  // Prescriptions state
  const [prescriptions, setPrescriptions] = useState([]);
  const [showRxForm, setShowRxForm] = useState(false);
  const [rxForm, setRxForm] = useState({ diagnosis: "", instructions: "", medications: [] });
  const [rxMedInput, setRxMedInput] = useState({ name: "", dosage: "", frequency: "", duration: "" });

  // Notes / Communication log state
  const [notes, setNotes] = useState([]);
  const [noteForm, setNoteForm] = useState({ type: "note", content: "", channel_target: "" });
  const [showNoteForm, setShowNoteForm] = useState(false);

  const { notify } = useToast();

  const fetchPatient = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/patients/${id}`);
      setPatient(res.data);
    } catch {
      notify("Failed to load patient.", "error");
    } finally {
      setLoading(false);
    }
  }, [id, notify]);

  const fetchDoctors = useCallback(async () => {
    try {
      const res = await api.get("/doctors/");
      setDoctors(res.data);
    } catch {
      notify("Failed to load doctors.", "error");
    }
  }, [notify]);

  const fetchPrescriptions = useCallback(async () => {
    try {
      const res = await api.get("/prescriptions", { params: { patient_id: id } });
      setPrescriptions(res.data);
    } catch { /* non-critical */ }
  }, [id]);

  const fetchNotes = useCallback(async () => {
    try {
      const res = await api.get("/notes", { params: { patient_id: id } });
      setNotes(res.data);
    } catch { /* non-critical */ }
  }, [id]);

  useEffect(() => {
    fetchPatient();
    fetchDoctors();
    fetchPrescriptions();
    fetchNotes();
  }, [fetchPatient, fetchDoctors, fetchPrescriptions, fetchNotes]);

  const addMedicine = () => {
    if (!medInput.medicine) return;
    setVisitForm((current) => ({
      ...current,
      prescription: [...current.prescription, { ...medInput }],
    }));
    setMedInput({ medicine: "", dosage: "", frequency: "", duration: "", notes: "" });
  };

  const removeMedicine = (index) => {
    setVisitForm((current) => ({
      ...current,
      prescription: current.prescription.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const addVisit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post("/visits/", {
        patient_id: id,
        doctor_id: visitForm.doctor_id || null,
        complaint: visitForm.complaint,
        diagnosis: visitForm.diagnosis,
        prescription: visitForm.prescription,
        tests_ordered: visitForm.tests_ordered,
        test_results: visitForm.test_results,
        doctor_notes: visitForm.doctor_notes,
        next_visit_date: visitForm.next_visit_date || null,
        fee: visitForm.fee ? parseInt(visitForm.fee) : 0,
      });
      setVisitForm(initialVisitForm);
      setShowVisitForm(false);
      notify("Visit saved.", "success");
      fetchPatient();
    } catch {
      notify("Failed to save visit.", "error");
    } finally {
      setSaving(false);
    }
  };

  // Prescription handlers
  const addRxMed = () => {
    if (!rxMedInput.name) return;
    setRxForm((f) => ({ ...f, medications: [...f.medications, { ...rxMedInput }] }));
    setRxMedInput({ name: "", dosage: "", frequency: "", duration: "" });
  };
  const removeRxMed = (i) => setRxForm((f) => ({ ...f, medications: f.medications.filter((_, idx) => idx !== i) }));
  const saveRx = async (e) => {
    e.preventDefault();
    try {
      await api.post("/prescriptions", { ...rxForm, patient_id: id });
      notify("Prescription saved.", "success");
      setRxForm({ diagnosis: "", instructions: "", medications: [] });
      setShowRxForm(false);
      fetchPrescriptions();
    } catch { notify("Failed to save prescription.", "error"); }
  };
  const deleteRx = async (rxId) => {
    if (!window.confirm("Delete this prescription?")) return;
    try {
      await api.delete(`/prescriptions/${rxId}`);
      notify("Deleted.", "success");
      fetchPrescriptions();
    } catch { notify("Failed to delete.", "error"); }
  };

  // Note handlers
  const saveNote = async (e) => {
    e.preventDefault();
    try {
      await api.post("/notes", { ...noteForm, patient_id: id, channel_target: noteForm.channel_target || null });
      notify(noteForm.type === "note" ? "Note saved." : "Message sent.", "success");
      setNoteForm({ type: "note", content: "", channel_target: "" });
      setShowNoteForm(false);
      fetchNotes();
    } catch (err) { notify(err?.response?.data?.detail || "Failed to save.", "error"); }
  };
  const deleteNote = async (noteId) => {
    try {
      await api.delete(`/notes/${noteId}`);
      fetchNotes();
    } catch { notify("Failed to delete.", "error"); }
  };

  if (loading) {
    return (
      <AppLayout title="Patient record" subtitle="Loading patient profile...">
        <SkeletonBlock className="skeleton-table" />
      </AppLayout>
    );
  }

  if (!patient) {
    return (
      <AppLayout title="Patient not found">
        <EmptyState title="Patient not found" description="This record may have been removed or belongs to another clinic." />
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title={patient.name}
      subtitle={`${patient.phone} - ${patient.total_visits || 0} recorded visits`}
      actions={
        <>
          <button className="btn btn-secondary" onClick={() => navigate("/patients")}>
            <ArrowLeft size={16} />
            Back
          </button>
          <button className="btn btn-primary" onClick={() => setShowVisitForm(true)}>
            <Plus size={16} />
            Add visit
          </button>
        </>
      }
    >
      <section className="profile-card">
        <div className="profile-left">
          <div className="avatar-lg">{patient.name.charAt(0).toUpperCase()}</div>
          <div>
            <h2 style={{ margin: 0 }}>{patient.name}</h2>
            <p className="muted" style={{ margin: "4px 0 0" }}>{patient.phone}</p>
          </div>
        </div>
        <div className="record-grid" style={{ margin: 0, flex: 1 }}>
          <Info label="Age" value={patient.age || "-"} />
          <Info label="Gender" value={patient.gender || "-"} />
          <Info label="Blood" value={patient.blood_group || "-"} />
          <Info label="Visits" value={patient.total_visits || 0} />
        </div>
      </section>

      <div className="info-grid">
        {patient.allergies && <Info label="Allergies" value={patient.allergies} />}
        {patient.chronic_conditions && <Info label="Chronic conditions" value={patient.chronic_conditions} />}
        {patient.emergency_contact && <Info label="Emergency contact" value={patient.emergency_contact} />}
      </div>

      <section className="table-panel">
        <div className="panel-header">
          <h2>Visit history</h2>
          <span className="badge">{patient.visits?.length || 0} visits</span>
        </div>
        {!patient.visits || patient.visits.length === 0 ? (
          <EmptyState
            title="No visits recorded yet"
            description="Add the first visit to build this patient's clinical history."
            action={<button className="btn btn-primary" onClick={() => setShowVisitForm(true)}>Add visit</button>}
          />
        ) : (
          <div className="timeline" style={{ padding: 12 }}>
            {patient.visits.map((visit) => (
              <article className="timeline-card" key={visit.id}>
                <div className="panel-header" style={{ padding: 0, borderBottom: 0 }}>
                  <div>
                    <h3>{new Date(visit.visit_date).toLocaleDateString("en-PK", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}</h3>
                    <p className="muted">Dr. {visit.doctor_name}</p>
                  </div>
                  {visit.fee > 0 && <span className="badge badge-success">PKR {visit.fee.toLocaleString()}</span>}
                </div>
                <div className="info-grid" style={{ marginTop: 14, marginBottom: 0 }}>
                  {visit.complaint && <Info label="Complaint" value={visit.complaint} />}
                  {visit.diagnosis && <Info label="Diagnosis" value={visit.diagnosis} />}
                  {visit.tests_ordered && <Info label="Tests" value={visit.tests_ordered} />}
                </div>
                {visit.prescription?.length > 0 && (
                  <div className="chip-row" style={{ marginTop: 12 }}>
                    {visit.prescription.map((medicine, index) => (
                      <span className="chip" key={`${medicine.medicine}-${index}`}>
                        {medicine.medicine} {medicine.dosage}
                      </span>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {/* ── Prescriptions ─────────────────────────────────────── */}
      <section className="table-panel">
        <div className="panel-header">
          <h2>Prescriptions</h2>
          <button className="btn btn-primary" style={{ fontSize: 12 }} onClick={() => setShowRxForm((s) => !s)}>
            <Plus size={14} /> {showRxForm ? "Close" : "New prescription"}
          </button>
        </div>

        {showRxForm && (
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)" }}>
            <form onSubmit={saveRx} className="form-stack" style={{ margin: 0 }}>
              <div className="form-grid">
                <input className="input" placeholder="Diagnosis" value={rxForm.diagnosis} onChange={(e) => setRxForm((f) => ({ ...f, diagnosis: e.target.value }))} />
                <input className="input" placeholder="Instructions" value={rxForm.instructions} onChange={(e) => setRxForm((f) => ({ ...f, instructions: e.target.value }))} />
              </div>
              <div className="action-row">
                <input className="input" placeholder="Medicine name *" value={rxMedInput.name} onChange={(e) => setRxMedInput((m) => ({ ...m, name: e.target.value }))} />
                <input className="input" placeholder="Dosage" value={rxMedInput.dosage} onChange={(e) => setRxMedInput((m) => ({ ...m, dosage: e.target.value }))} />
                <input className="input" placeholder="Frequency" value={rxMedInput.frequency} onChange={(e) => setRxMedInput((m) => ({ ...m, frequency: e.target.value }))} />
                <input className="input" placeholder="Duration" value={rxMedInput.duration} onChange={(e) => setRxMedInput((m) => ({ ...m, duration: e.target.value }))} />
                <button type="button" className="btn btn-secondary" onClick={addRxMed}><Plus size={14} /></button>
              </div>
              <div className="chip-row">
                {rxForm.medications.map((m, i) => (
                  <span className="chip" key={i}>{m.name} {m.dosage}
                    <button type="button" onClick={() => removeRxMed(i)}><X size={11} /></button>
                  </span>
                ))}
              </div>
              <div className="action-row">
                <button className="btn btn-primary" type="submit">Save prescription</button>
                <button className="btn btn-secondary" type="button" onClick={() => setShowRxForm(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {prescriptions.length === 0 ? (
          <p style={{ padding: "14px 20px", color: "var(--muted)", fontSize: 13 }}>No prescriptions yet.</p>
        ) : (
          <div style={{ padding: "12px 20px" }} className="form-stack">
            {prescriptions.map((rx) => (
              <div key={rx.id} style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: 8, padding: "12px 16px" }}>
                <div className="panel-header" style={{ padding: 0, borderBottom: 0, marginBottom: 8 }}>
                  <div>
                    <strong>{rx.diagnosis || "Prescription"}</strong>
                    <p className="muted" style={{ fontSize: 12, margin: 0 }}>{new Date(rx.created_at).toLocaleDateString()}</p>
                  </div>
                  <button className="icon-btn btn-danger" onClick={() => deleteRx(rx.id)}><Trash2 size={13} /></button>
                </div>
                <div className="chip-row">
                  {(rx.medications || []).map((m, i) => (
                    <span className="chip" key={i}>{m.name} {m.dosage && `— ${m.dosage}`} {m.frequency && `× ${m.frequency}`}</span>
                  ))}
                </div>
                {rx.instructions && <p style={{ fontSize: 12, marginTop: 8, color: "var(--muted)" }}>{rx.instructions}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Communication log ─────────────────────────────────── */}
      <section className="table-panel">
        <div className="panel-header">
          <h2>Communication log</h2>
          <button className="btn btn-primary" style={{ fontSize: 12 }} onClick={() => setShowNoteForm((s) => !s)}>
            <MessageSquare size={14} /> {showNoteForm ? "Close" : "Add note / message"}
          </button>
        </div>

        {showNoteForm && (
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)" }}>
            <form onSubmit={saveNote} className="form-stack" style={{ margin: 0 }}>
              <div className="form-grid">
                <select className="select" value={noteForm.type} onChange={(e) => setNoteForm((f) => ({ ...f, type: e.target.value }))}>
                  <option value="note">Internal note</option>
                  <option value="call">Call log</option>
                  <option value="sms">SMS</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="email">Email</option>
                </select>
                {["sms", "whatsapp", "email"].includes(noteForm.type) && (
                  <input
                    className="input"
                    placeholder={noteForm.type === "email" ? "Email address" : "Phone e.g. +923001234567"}
                    value={noteForm.channel_target}
                    onChange={(e) => setNoteForm((f) => ({ ...f, channel_target: e.target.value }))}
                  />
                )}
              </div>
              <textarea
                className="input textarea"
                placeholder={noteForm.type === "note" ? "Note content..." : "Message to send..."}
                value={noteForm.content}
                onChange={(e) => setNoteForm((f) => ({ ...f, content: e.target.value }))}
                required
              />
              <div className="action-row">
                <button className="btn btn-primary" type="submit">
                  {["sms", "whatsapp", "email"].includes(noteForm.type) ? "Send message" : "Save note"}
                </button>
                <button className="btn btn-secondary" type="button" onClick={() => setShowNoteForm(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {notes.length === 0 ? (
          <p style={{ padding: "14px 20px", color: "var(--muted)", fontSize: 13 }}>No notes or messages yet.</p>
        ) : (
          <div style={{ padding: "12px 20px" }} className="form-stack">
            {notes.map((n) => (
              <div key={n.id} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <span className={`badge ${noteTypeBadge(n.type)}`} style={{ flexShrink: 0, marginTop: 2 }}>{n.type}</span>
                <div style={{ flex: 1 }}>
                  <p style={{ margin: 0, fontSize: 13 }}>{n.content}</p>
                  <p style={{ margin: "3px 0 0", fontSize: 11, color: "var(--muted)" }}>
                    {new Date(n.created_at).toLocaleString()}
                    {n.channel_target && ` → ${n.channel_target}`}
                    {n.delivery_status && ` (${n.delivery_status})`}
                  </p>
                </div>
                <button className="icon-btn btn-danger" onClick={() => deleteNote(n.id)}><Trash2 size={12} /></button>
              </div>
            ))}
          </div>
        )}
      </section>

      {showVisitForm && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <h2>Record new visit</h2>
                <p>{patient.name}</p>
              </div>
              <button className="icon-btn" onClick={() => setShowVisitForm(false)}><X size={16} /></button>
            </div>
            <form onSubmit={addVisit}>
              <div className="modal-body form-stack">
                <div className="form-grid">
                  <select className="select" value={visitForm.doctor_id} onChange={(e) => setVisitForm({ ...visitForm, doctor_id: e.target.value })}>
                    <option value="">Select doctor</option>
                    {doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>Dr. {doctor.name} - {doctor.specialty}</option>)}
                  </select>
                  <input className="input" type="number" placeholder="Consultation fee" value={visitForm.fee} onChange={(e) => setVisitForm({ ...visitForm, fee: e.target.value })} />
                </div>
                <textarea className="input textarea" placeholder="Patient complaint" value={visitForm.complaint} onChange={(e) => setVisitForm({ ...visitForm, complaint: e.target.value })} />
                <textarea className="input textarea" placeholder="Diagnosis" value={visitForm.diagnosis} onChange={(e) => setVisitForm({ ...visitForm, diagnosis: e.target.value })} />
                <div className="field">
                  <label>Prescription</label>
                  <div className="action-row">
                    <input className="input" placeholder="Medicine" value={medInput.medicine} onChange={(e) => setMedInput({ ...medInput, medicine: e.target.value })} />
                    <input className="input" placeholder="Dosage" value={medInput.dosage} onChange={(e) => setMedInput({ ...medInput, dosage: e.target.value })} />
                    <input className="input" placeholder="Frequency" value={medInput.frequency} onChange={(e) => setMedInput({ ...medInput, frequency: e.target.value })} />
                    <button type="button" className="btn btn-secondary" onClick={addMedicine}><Plus size={16} /> Add</button>
                  </div>
                  <div className="chip-row">
                    {visitForm.prescription.map((medicine, index) => (
                      <span className="chip" key={`${medicine.medicine}-${index}`}>
                        {medicine.medicine}
                        <button type="button" onClick={() => removeMedicine(index)}><Trash2 size={12} /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <div className="form-grid">
                  <input className="input" placeholder="Tests ordered" value={visitForm.tests_ordered} onChange={(e) => setVisitForm({ ...visitForm, tests_ordered: e.target.value })} />
                  <input className="input" type="date" value={visitForm.next_visit_date} onChange={(e) => setVisitForm({ ...visitForm, next_visit_date: e.target.value })} />
                </div>
                <textarea className="input textarea" placeholder="Doctor notes" value={visitForm.doctor_notes} onChange={(e) => setVisitForm({ ...visitForm, doctor_notes: e.target.value })} />
              </div>
              <div className="modal-footer">
                <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? "Saving..." : "Save visit"}</button>
                <button className="btn btn-secondary" type="button" onClick={() => setShowVisitForm(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

function Info({ label, value }) {
  return (
    <div className="record-card">
      <p className="record-label">{label}</p>
      <p className="record-value" style={{ fontSize: 16 }}>{value}</p>
    </div>
  );
}

function noteTypeBadge(type) {
  if (type === "sms" || type === "whatsapp") return "badge-success";
  if (type === "email") return "";
  if (type === "call") return "badge-warning";
  return "";
}
