import { useCallback, useEffect, useState } from "react";
import { Edit3, KeyRound, Plus, Trash2, X } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const emptyForm = {
  name: "",
  specialty: "",
  qualification: "",
  fee: "",
  bio: "",
  treatments: [],
  timings: [],
  slot_capacity: 1,
};

export default function Doctors() {
  const [doctors, setDoctors] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [timingInput, setTimingInput] = useState({
    day: "Monday",
    from: "09:00 AM",
    to: "05:00 PM",
  });
  const [editId, setEditId] = useState(null);
  const [loginModal, setLoginModal] = useState(null); // doctor object
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [loginSaving, setLoginSaving] = useState(false);
  const { notify } = useToast();

  const fetchDoctors = useCallback(async () => {
    setLoading(true);
    try {
      const [docRes, svcRes] = await Promise.all([api.get("/doctors/"), api.get("/services/")]);
      setDoctors(docRes.data);
      setServices(svcRes.data);
    } catch {
      notify("Failed to load doctors.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchDoctors();
  }, [fetchDoctors]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditId(null);
    setTimingInput({ day: "Monday", from: "09:00 AM", to: "05:00 PM" });
  };

  const toggleTreatment = (name) => {
    setForm((f) => ({
      ...f,
      treatments: f.treatments.includes(name)
        ? f.treatments.filter((t) => t !== name)
        : [...f.treatments, name],
    }));
  };

  const payloadFromForm = () => ({
    name: form.name,
    specialty: form.specialty,
    qualification: form.qualification,
    fee: form.fee,
    bio: form.bio,
    treatments: form.treatments,
    timings: form.timings,
    slot_capacity: Number(form.slot_capacity) || 1,
    available_slots: [],
  });

  const saveDoctor = async (event) => {
    event.preventDefault();
    try {
      if (editId) {
        await api.put(`/doctors/${editId}`, payloadFromForm());
        notify("Doctor updated.", "success");
      } else {
        await api.post("/doctors/", payloadFromForm());
        notify("Doctor added.", "success");
      }
      resetForm();
      setShowForm(false);
      fetchDoctors();
    } catch {
      notify(editId ? "Failed to update doctor." : "Failed to add doctor.", "error");
    }
  };

  const removeDoctor = async (id) => {
    if (!window.confirm("Remove this doctor?")) return;
    try {
      await api.delete(`/doctors/${id}`);
      notify("Doctor removed.", "success");
      fetchDoctors();
    } catch {
      notify("Failed to remove doctor.", "error");
    }
  };

  const editDoctor = (doctor) => {
    setEditId(doctor.id);
    setForm({
      name: doctor.name,
      specialty: doctor.specialty,
      qualification: doctor.qualification || "",
      fee: doctor.fee || "",
      bio: doctor.bio || "",
      treatments: doctor.treatments || [],
      timings: doctor.timings || [],
      slot_capacity: doctor.slot_capacity || 1,
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const createDoctorLogin = async () => {
    if (!loginForm.email || !loginForm.password) {
      notify("Email and password are required.", "error");
      return;
    }
    setLoginSaving(true);
    try {
      await api.post(`/doctors/${loginModal.id}/create-login`, loginForm);
      notify("Doctor login created successfully.", "success");
      setLoginModal(null);
      setLoginForm({ email: "", password: "" });
      fetchDoctors();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to create login.", "error");
    } finally {
      setLoginSaving(false);
    }
  };

  const addTiming = () => {
    setForm((current) => ({
      ...current,
      timings: [...current.timings, { ...timingInput }],
    }));
  };

  const removeTiming = (index) => {
    setForm((current) => ({
      ...current,
      timings: current.timings.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  return (
    <AppLayout
      title="Doctors"
      subtitle="Manage specialties, fees, treatments, and chatbot booking hours."
      actions={
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} />
          {showForm ? "Close form" : "Add doctor"}
        </button>
      }
    >
      {showForm && (
        <section className="form-panel">
          <h2>{editId ? "Edit doctor" : "Add new doctor"}</h2>
          <form onSubmit={saveDoctor} className="form-stack">
            <div className="form-grid">
              <input className="input" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <input className="input" placeholder="Specialty" value={form.specialty} onChange={(e) => setForm({ ...form, specialty: e.target.value })} required />
              <input className="input" placeholder="Qualification" value={form.qualification} onChange={(e) => setForm({ ...form, qualification: e.target.value })} />
              <input className="input" placeholder="Fee e.g. 1500 PKR" value={form.fee} onChange={(e) => setForm({ ...form, fee: e.target.value })} />
            </div>
            <textarea className="input textarea" placeholder="Short bio" value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />

            <div className="field">
              <label>Patients per time-slot</label>
              <input
                className="input" type="number" min={1} max={50}
                style={{ maxWidth: 140 }}
                value={form.slot_capacity}
                onChange={(e) => setForm({ ...form, slot_capacity: e.target.value })}
              />
              <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 0" }}>
                How many patients this doctor can see in the same slot. Leave at 1
                for one-at-a-time; raise it to accept several bookings per slot.
              </p>
            </div>

            <div className="field">
              <label>Services this doctor can perform</label>
              {services.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 0" }}>
                  No services added yet. Go to <strong>Services</strong> to build your clinic's checklist first.
                </p>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
                  {services.map((s) => {
                    const checked = form.treatments.includes(s.name);
                    return (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => toggleTreatment(s.name)}
                        style={{
                          padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 600,
                          border: "2px solid",
                          borderColor: checked ? "var(--primary)" : "var(--line)",
                          background: checked ? "var(--primary)" : "var(--surface-2)",
                          color: checked ? "#fff" : "var(--text)",
                          cursor: "pointer", transition: "all 0.15s",
                        }}
                      >
                        {checked ? "✓ " : ""}{s.name}
                      </button>
                    );
                  })}
                </div>
              )}
              {form.treatments.length > 0 && (
                <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>
                  Selected: {form.treatments.join(", ")}
                </p>
              )}
            </div>

            <div className="field">
              <label>Clinic timings</label>
              <div className="action-row">
                <select className="select" value={timingInput.day} onChange={(e) => setTimingInput({ ...timingInput, day: e.target.value })}>
                  {days.map((day) => <option key={day}>{day}</option>)}
                </select>
                <input className="input" value={timingInput.from} onChange={(e) => setTimingInput({ ...timingInput, from: e.target.value })} />
                <input className="input" value={timingInput.to} onChange={(e) => setTimingInput({ ...timingInput, to: e.target.value })} />
                <button type="button" className="btn btn-secondary" onClick={addTiming}>Add day</button>
              </div>
              <div className="chip-row">
                {form.timings.map((timing, index) => (
                  <span className="chip" key={`${timing.day}-${index}`}>
                    {timing.day} {timing.from}-{timing.to}
                    <button type="button" onClick={() => removeTiming(index)} aria-label="Remove timing">
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="action-row">
              <button className="btn btn-primary" type="submit">Save doctor</button>
              <button className="btn btn-secondary" type="button" onClick={() => { resetForm(); setShowForm(false); }}>Cancel</button>
            </div>
          </form>
        </section>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Clinic doctors</h2>
          <span className="badge">{doctors.length} active</span>
        </div>
        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : doctors.length === 0 ? (
          <EmptyState
            title="No doctors yet"
            description="Add your first doctor so the chatbot can recommend the right specialist and show real appointment slots."
            action={<button className="btn btn-primary" onClick={() => setShowForm(true)}>Add first doctor</button>}
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>{["Doctor", "Specialty", "Fee", "Treatments", "Timings", "Visits", "Appointments", "Actions"].map((h) => <th key={h}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {doctors.map((doctor) => (
                <tr key={doctor.id}>
                  <td data-label="Doctor"><strong>Dr. {doctor.name}</strong><br /><span className="muted">{doctor.qualification || "Qualification not set"}</span></td>
                  <td data-label="Specialty">{doctor.specialty}</td>
                  <td data-label="Fee">{doctor.fee || "-"}</td>
                  <td data-label="Treatments"><div className="chip-row">{(doctor.treatments || []).slice(0, 3).map((t) => <span className="chip" key={t}>{t}</span>)}</div></td>
                  <td data-label="Timings">{(doctor.timings || []).length ? `${doctor.timings.length} day(s)` : "-"}</td>
                  <td data-label="Visits">{doctor.total_visits || 0}</td>
                  <td data-label="Appointments">{doctor.total_appointments || 0}</td>
                  <td data-label="Actions">
                    <div className="action-row" style={{ justifyContent: "flex-end" }}>
                      {doctor.has_login
                        ? <span className="badge badge-success" style={{ fontSize: 11 }}>Login active</span>
                        : <button className="icon-btn" title="Create doctor login" onClick={() => { setLoginModal(doctor); setLoginForm({ email: "", password: "" }); }}><KeyRound size={15} /></button>
                      }
                      <button className="icon-btn" onClick={() => editDoctor(doctor)} title="Edit doctor"><Edit3 size={15} /></button>
                      <button className="icon-btn btn-danger" onClick={() => removeDoctor(doctor.id)} title="Remove doctor"><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      {loginModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <h2>Create doctor login</h2>
                <p>Dr. {loginModal.name} — {loginModal.specialty}</p>
              </div>
              <button className="icon-btn" onClick={() => setLoginModal(null)}><X size={16} /></button>
            </div>
            <div className="modal-body form-stack">
              <input
                className="input"
                type="email"
                placeholder="Doctor's email address"
                value={loginForm.email}
                onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
              />
              <input
                className="input"
                type="password"
                placeholder="Password (min 8 characters)"
                value={loginForm.password}
                onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              />
              <p style={{ fontSize: 12, color: "var(--muted)" }}>
                The doctor will use these credentials to log in and see their own schedule and patients.
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={createDoctorLogin} disabled={loginSaving}>
                {loginSaving ? "Creating..." : "Create login"}
              </button>
              <button className="btn btn-secondary" onClick={() => setLoginModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
