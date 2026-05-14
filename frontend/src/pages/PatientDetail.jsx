import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Plus, Trash2, X } from "lucide-react";
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

  useEffect(() => {
    fetchPatient();
    fetchDoctors();
  }, [fetchPatient, fetchDoctors]);

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
