import { useCallback, useEffect, useState } from "react";
import { Edit3, Plus, Trash2, X } from "lucide-react";
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
  treatments: "",
  timings: [],
};

export default function Doctors() {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [timingInput, setTimingInput] = useState({
    day: "Monday",
    from: "09:00 AM",
    to: "05:00 PM",
  });
  const [editId, setEditId] = useState(null);
  const { notify } = useToast();

  const fetchDoctors = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/doctors/");
      setDoctors(res.data);
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

  const payloadFromForm = () => ({
    name: form.name,
    specialty: form.specialty,
    qualification: form.qualification,
    fee: form.fee,
    bio: form.bio,
    treatments: form.treatments.split(",").map((item) => item.trim()).filter(Boolean),
    timings: form.timings,
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
      treatments: doctor.treatments ? doctor.treatments.join(", ") : "",
      timings: doctor.timings || [],
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
            <input className="input" placeholder="Treatments, comma separated" value={form.treatments} onChange={(e) => setForm({ ...form, treatments: e.target.value })} />

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
    </AppLayout>
  );
}
