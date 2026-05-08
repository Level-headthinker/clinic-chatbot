import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { Plus, ArrowLeft, Trash2 } from "lucide-react";

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showVisitForm, setShowVisitForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [visitForm, setVisitForm] = useState({
    complaint: "",
    diagnosis: "",
    tests_ordered: "",
    test_results: "",
    doctor_notes: "",
    next_visit_date: "",
    fee: "",
    doctor_id: "",
    prescription: []
  });

  const [medInput, setMedInput] = useState({
    medicine: "", dosage: "", frequency: "", duration: "", notes: ""
  });

  useEffect(() => {
    fetchPatient();
    fetchDoctors();
  }, []);

  const fetchPatient = async () => {
    try {
      const res = await api.get(`/patients/${id}`);
      setPatient(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDoctors = async () => {
    try {
      const res = await api.get("/doctors/");
      setDoctors(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const addMedicine = () => {
    if (!medInput.medicine) return;
    setVisitForm({
      ...visitForm,
      prescription: [...visitForm.prescription, { ...medInput }]
    });
    setMedInput({ medicine: "", dosage: "", frequency: "", duration: "", notes: "" });
  };

  const removeMedicine = (index) => {
    setVisitForm({
      ...visitForm,
      prescription: visitForm.prescription.filter((_, i) => i !== index)
    });
  };

  const handleAddVisit = async (e) => {
    e.preventDefault();
    setError("");
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
        fee: visitForm.fee ? parseInt(visitForm.fee) : 0
      });
      setVisitForm({
        complaint: "", diagnosis: "", tests_ordered: "",
        test_results: "", doctor_notes: "", next_visit_date: "",
        fee: "", doctor_id: "", prescription: []
      });
      setShowVisitForm(false);
      fetchPatient();
    } catch (err) {
      setError("Failed to save visit");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}><p>Loading patient...</p></div>
    </div>
  );

  if (!patient) return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}><p>Patient not found.</p></div>
    </div>
  );

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>

        {/* Back button */}
        <button
          onClick={() => navigate("/patients")}
          style={styles.backBtn}
        >
          <ArrowLeft size={16} /> Back to Patients
        </button>

        {/* Patient profile card */}
        <div style={styles.profileCard}>
          <div style={styles.profileLeft}>
            <div style={styles.bigAvatar}>
              {patient.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={styles.patientName}>{patient.name}</h2>
              <p style={styles.patientPhone}>📞 {patient.phone}</p>
              {patient.last_visit && (
                <p style={styles.lastVisit}>
                  Last visit: {new Date(patient.last_visit).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
          <div style={styles.profileStats}>
            <div style={styles.statBox}>
              <p style={styles.statNum}>{patient.total_visits}</p>
              <p style={styles.statLbl}>Total Visits</p>
            </div>
            <div style={styles.statBox}>
              <p style={styles.statNum}>{patient.age || "—"}</p>
              <p style={styles.statLbl}>Age</p>
            </div>
            <div style={styles.statBox}>
              <p style={{ ...styles.statNum, color: "#dc2626" }}>
                {patient.blood_group || "—"}
              </p>
              <p style={styles.statLbl}>Blood Group</p>
            </div>
            <div style={styles.statBox}>
              <p style={styles.statNum}>{patient.gender || "—"}</p>
              <p style={styles.statLbl}>Gender</p>
            </div>
          </div>
        </div>

        {/* Medical info row */}
        <div style={styles.infoRow}>
          {patient.allergies && (
            <div style={styles.infoBox}>
              <p style={styles.infoLabel}>⚠️ Allergies</p>
              <p style={styles.infoValue}>{patient.allergies}</p>
            </div>
          )}
          {patient.chronic_conditions && (
            <div style={styles.infoBox}>
              <p style={styles.infoLabel}>🩺 Chronic Conditions</p>
              <p style={styles.infoValue}>{patient.chronic_conditions}</p>
            </div>
          )}
          {patient.emergency_contact && (
            <div style={styles.infoBox}>
              <p style={styles.infoLabel}>🚨 Emergency Contact</p>
              <p style={styles.infoValue}>{patient.emergency_contact}</p>
            </div>
          )}
        </div>

        {/* Add visit button */}
        <div style={styles.visitHeader}>
          <h3 style={styles.visitTitle}>Visit History</h3>
          <button
            onClick={() => setShowVisitForm(!showVisitForm)}
            style={styles.addButton}
          >
            <Plus size={16} /> Add Visit
          </button>
        </div>

        {/* Add visit form */}
        {showVisitForm && (
          <div style={styles.formCard}>
            <h4 style={styles.formTitle}>Record New Visit</h4>
            {error && <p style={styles.error}>{error}</p>}
            <form onSubmit={handleAddVisit} style={styles.form}>

              <div style={styles.formGrid}>
                <div style={styles.field}>
                  <label style={styles.label}>Doctor</label>
                  <select
                    style={styles.input}
                    value={visitForm.doctor_id}
                    onChange={(e) => setVisitForm({ ...visitForm, doctor_id: e.target.value })}
                  >
                    <option value="">Select Doctor</option>
                    {doctors.map(d => (
                      <option key={d.id} value={d.id}>
                        Dr. {d.name} — {d.specialty}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Consultation Fee (PKR)</label>
                  <input
                    style={styles.input}
                    type="number"
                    placeholder="e.g. 1000"
                    value={visitForm.fee}
                    onChange={(e) => setVisitForm({ ...visitForm, fee: e.target.value })}
                  />
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Patient Complaint</label>
                <textarea
                  style={styles.textarea}
                  placeholder="What is the patient complaining about?"
                  value={visitForm.complaint}
                  onChange={(e) => setVisitForm({ ...visitForm, complaint: e.target.value })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Diagnosis</label>
                <textarea
                  style={styles.textarea}
                  placeholder="Doctor's diagnosis"
                  value={visitForm.diagnosis}
                  onChange={(e) => setVisitForm({ ...visitForm, diagnosis: e.target.value })}
                />
              </div>

              {/* Prescription */}
              <div style={styles.field}>
                <label style={styles.label}>Prescription</label>
                <div style={styles.medRow}>
                  <input
                    style={{ ...styles.input, flex: 2 }}
                    placeholder="Medicine name"
                    value={medInput.medicine}
                    onChange={(e) => setMedInput({ ...medInput, medicine: e.target.value })}
                  />
                  <input
                    style={{ ...styles.input, flex: 1 }}
                    placeholder="Dosage"
                    value={medInput.dosage}
                    onChange={(e) => setMedInput({ ...medInput, dosage: e.target.value })}
                  />
                  <input
                    style={{ ...styles.input, flex: 1 }}
                    placeholder="Frequency"
                    value={medInput.frequency}
                    onChange={(e) => setMedInput({ ...medInput, frequency: e.target.value })}
                  />
                  <input
                    style={{ ...styles.input, flex: 1 }}
                    placeholder="Duration"
                    value={medInput.duration}
                    onChange={(e) => setMedInput({ ...medInput, duration: e.target.value })}
                  />
                  <button
                    type="button"
                    onClick={addMedicine}
                    style={styles.addMedBtn}
                  >
                    + Add
                  </button>
                </div>

                {visitForm.prescription.length > 0 && (
                  <div style={styles.prescriptionList}>
                    {visitForm.prescription.map((med, i) => (
                      <div key={i} style={styles.medItem}>
                        <div>
                          <strong>{med.medicine}</strong>
                          <span style={styles.medDetail}>
                            {med.dosage} · {med.frequency} · {med.duration}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeMedicine(i)}
                          style={styles.removeMedBtn}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={styles.formGrid}>
                <div style={styles.field}>
                  <label style={styles.label}>Tests Ordered</label>
                  <input
                    style={styles.input}
                    placeholder="e.g. CBC, Blood Sugar, X-Ray"
                    value={visitForm.tests_ordered}
                    onChange={(e) => setVisitForm({ ...visitForm, tests_ordered: e.target.value })}
                  />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Next Visit Date</label>
                  <input
                    type="date"
                    style={styles.input}
                    value={visitForm.next_visit_date}
                    onChange={(e) => setVisitForm({ ...visitForm, next_visit_date: e.target.value })}
                  />
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Doctor Notes (Private)</label>
                <textarea
                  style={styles.textarea}
                  placeholder="Private notes — not visible to patient"
                  value={visitForm.doctor_notes}
                  onChange={(e) => setVisitForm({ ...visitForm, doctor_notes: e.target.value })}
                />
              </div>

              <div style={styles.formButtons}>
                <button
                  type="submit"
                  style={saving ? styles.savingBtn : styles.submitButton}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Visit"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowVisitForm(false)}
                  style={styles.cancelButton}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Visit timeline */}
        {patient.visits && patient.visits.length === 0 ? (
          <div style={styles.emptyVisits}>
            <p>No visits recorded yet.</p>
            <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
              Click "Add Visit" to record the first visit.
            </p>
          </div>
        ) : (
          <div style={styles.timeline}>
            {patient.visits && patient.visits.map((v, i) => (
              <div key={v.id} style={styles.timelineItem}>
                <div style={styles.timelineDot} />
                {i < patient.visits.length - 1 && (
                  <div style={styles.timelineLine} />
                )}
                <div style={styles.visitCard}>
                  <div style={styles.visitCardHeader}>
                    <div>
                      <p style={styles.visitDate}>
                        📅 {new Date(v.visit_date).toLocaleDateString("en-PK", {
                          weekday: "long", year: "numeric",
                          month: "long", day: "numeric"
                        })}
                      </p>
                      <p style={styles.visitDoctor}>
                        Dr. {v.doctor_name}
                      </p>
                    </div>
                    {v.fee > 0 && (
                      <span style={styles.feeBadge}>
                        PKR {v.fee.toLocaleString()}
                      </span>
                    )}
                  </div>

                  <div style={styles.visitGrid}>
                    {v.complaint && (
                      <div style={styles.visitSection}>
                        <p style={styles.visitSectionLabel}>Complaint</p>
                        <p style={styles.visitSectionValue}>{v.complaint}</p>
                      </div>
                    )}
                    {v.diagnosis && (
                      <div style={styles.visitSection}>
                        <p style={styles.visitSectionLabel}>Diagnosis</p>
                        <p style={styles.visitSectionValue}>{v.diagnosis}</p>
                      </div>
                    )}
                    {v.tests_ordered && (
                      <div style={styles.visitSection}>
                        <p style={styles.visitSectionLabel}>Tests Ordered</p>
                        <p style={styles.visitSectionValue}>{v.tests_ordered}</p>
                      </div>
                    )}
                    {v.next_visit_date && (
                      <div style={styles.visitSection}>
                        <p style={styles.visitSectionLabel}>Next Visit</p>
                        <p style={{ ...styles.visitSectionValue, color: "#2563eb", fontWeight: "600" }}>
                          {v.next_visit_date}
                        </p>
                      </div>
                    )}
                  </div>

                  {v.prescription && v.prescription.length > 0 && (
                    <div style={styles.prescriptionBox}>
                      <p style={styles.visitSectionLabel}>💊 Prescription</p>
                      <div style={styles.prescriptionGrid}>
                        {v.prescription.map((med, mi) => (
                          <div key={mi} style={styles.prescriptionCard}>
                            <strong style={{ fontSize: "13px" }}>{med.medicine}</strong>
                            <p style={{ fontSize: "11px", color: "#64748b", margin: "2px 0 0 0" }}>
                              {med.dosage} · {med.frequency} · {med.duration}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {v.doctor_notes && (
                    <div style={styles.notesBox}>
                      <p style={styles.visitSectionLabel}>🔒 Doctor Notes (Private)</p>
                      <p style={{ fontSize: "13px", color: "#475569" }}>{v.doctor_notes}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  layout: { display: "flex", minHeight: "100vh", backgroundColor: "#f8fafc" },
  main: { marginLeft: "240px", padding: "32px", flex: 1 },
  backBtn: {
    display: "flex", alignItems: "center", gap: "6px",
    backgroundColor: "transparent", border: "none",
    color: "#64748b", cursor: "pointer", fontSize: "14px",
    marginBottom: "20px", padding: 0
  },
  profileCard: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "24px", marginBottom: "16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    display: "flex", justifyContent: "space-between",
    alignItems: "center", flexWrap: "wrap", gap: "20px"
  },
  profileLeft: { display: "flex", alignItems: "center", gap: "16px" },
  bigAvatar: {
    width: "60px", height: "60px", borderRadius: "50%",
    backgroundColor: "#eff6ff", color: "#2563eb",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontWeight: "700", fontSize: "24px", flexShrink: 0
  },
  patientName: { fontSize: "20px", fontWeight: "700", color: "#1e293b", margin: "0 0 4px 0" },
  patientPhone: { fontSize: "14px", color: "#64748b", margin: "0 0 4px 0" },
  lastVisit: { fontSize: "12px", color: "#94a3b8", margin: 0 },
  profileStats: { display: "flex", gap: "20px" },
  statBox: { textAlign: "center" },
  statNum: { fontSize: "22px", fontWeight: "700", color: "#1e293b", margin: 0 },
  statLbl: { fontSize: "11px", color: "#94a3b8", margin: 0, textTransform: "uppercase" },
  infoRow: {
    display: "flex", gap: "12px", marginBottom: "24px", flexWrap: "wrap"
  },
  infoBox: {
    backgroundColor: "#fff", borderRadius: "10px",
    padding: "14px 18px", flex: 1, minWidth: "200px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  infoLabel: { fontSize: "11px", color: "#94a3b8", margin: "0 0 4px 0", textTransform: "uppercase" },
  infoValue: { fontSize: "14px", color: "#1e293b", margin: 0, fontWeight: "500" },
  visitHeader: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: "16px"
  },
  visitTitle: { fontSize: "18px", fontWeight: "700", color: "#1e293b", margin: 0 },
  addButton: {
    display: "flex", alignItems: "center", gap: "8px",
    backgroundColor: "#2563eb", color: "#fff", border: "none",
    padding: "10px 16px", borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px"
  },
  formCard: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "24px", marginBottom: "24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  formTitle: { fontSize: "15px", fontWeight: "600", marginBottom: "16px", color: "#1e293b" },
  error: { color: "#dc2626", fontSize: "14px", marginBottom: "12px" },
  form: { display: "flex", flexDirection: "column", gap: "14px" },
  formGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" },
  field: { display: "flex", flexDirection: "column", gap: "5px" },
  label: { fontSize: "12px", fontWeight: "600", color: "#374151" },
  input: {
    padding: "10px 12px", borderRadius: "8px",
    border: "1px solid #d1d5db", fontSize: "14px",
    outline: "none", boxSizing: "border-box"
  },
  textarea: {
    padding: "10px 12px", borderRadius: "8px",
    border: "1px solid #d1d5db", fontSize: "14px",
    outline: "none", resize: "vertical", minHeight: "80px"
  },
  medRow: { display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" },
  addMedBtn: {
    backgroundColor: "#eff6ff", color: "#2563eb",
    border: "1px solid #bfdbfe", padding: "10px 14px",
    borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "13px", whiteSpace: "nowrap"
  },
  prescriptionList: { display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" },
  medItem: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", backgroundColor: "#f8fafc",
    padding: "8px 12px", borderRadius: "8px",
    border: "1px solid #e2e8f0"
  },
  medDetail: { fontSize: "12px", color: "#64748b", marginLeft: "8px" },
  removeMedBtn: {
    backgroundColor: "#fee2e2", color: "#dc2626",
    border: "none", padding: "4px 6px",
    borderRadius: "4px", cursor: "pointer"
  },
  formButtons: { display: "flex", gap: "12px" },
  submitButton: {
    backgroundColor: "#2563eb", color: "#fff", border: "none",
    padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px"
  },
  savingBtn: {
    backgroundColor: "#93c5fd", color: "#fff", border: "none",
    padding: "10px 20px", borderRadius: "8px",
    fontWeight: "600", fontSize: "14px", cursor: "not-allowed"
  },
  cancelButton: {
    backgroundColor: "#f1f5f9", color: "#374151", border: "none",
    padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px"
  },
  emptyVisits: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "40px", textAlign: "center",
    color: "#64748b", fontSize: "15px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  timeline: { display: "flex", flexDirection: "column", gap: "0" },
  timelineItem: { display: "flex", gap: "16px", position: "relative", paddingBottom: "24px" },
  timelineDot: {
    width: "14px", height: "14px", borderRadius: "50%",
    backgroundColor: "#2563eb", flexShrink: 0, marginTop: "18px",
    border: "3px solid #eff6ff"
  },
  timelineLine: {
    position: "absolute", left: "6px", top: "32px",
    bottom: "0", width: "2px", backgroundColor: "#e2e8f0"
  },
  visitCard: {
    flex: 1, backgroundColor: "#fff", borderRadius: "12px",
    padding: "20px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    border: "1px solid #f1f5f9"
  },
  visitCardHeader: {
    display: "flex", justifyContent: "space-between",
    alignItems: "flex-start", marginBottom: "14px"
  },
  visitDate: { fontSize: "14px", fontWeight: "600", color: "#1e293b", margin: "0 0 3px 0" },
  visitDoctor: { fontSize: "13px", color: "#2563eb", margin: 0 },
  feeBadge: {
    backgroundColor: "#f0fdf4", color: "#16a34a",
    padding: "4px 12px", borderRadius: "20px",
    fontSize: "13px", fontWeight: "700"
  },
  visitGrid: {
    display: "grid", gridTemplateColumns: "1fr 1fr",
    gap: "12px", marginBottom: "14px"
  },
  visitSection: {},
  visitSectionLabel: {
    fontSize: "10px", color: "#94a3b8", margin: "0 0 3px 0",
    textTransform: "uppercase", fontWeight: "600"
  },
  visitSectionValue: { fontSize: "13px", color: "#374151", margin: 0 },
  prescriptionBox: {
    backgroundColor: "#f8fafc", borderRadius: "8px",
    padding: "12px", marginBottom: "10px"
  },
  prescriptionGrid: {
    display: "flex", flexWrap: "wrap",
    gap: "8px", marginTop: "8px"
  },
  prescriptionCard: {
    backgroundColor: "#fff", border: "1px solid #e2e8f0",
    borderRadius: "8px", padding: "8px 12px", minWidth: "150px"
  },
  notesBox: {
    backgroundColor: "#fffbeb", borderRadius: "8px",
    padding: "12px", border: "1px solid #fde68a"
  },
};