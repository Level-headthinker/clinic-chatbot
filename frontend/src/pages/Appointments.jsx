import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { useNavigate } from "react-router-dom";

const STATUS_COLORS = {
  pending: { bg: "#fef9c3", color: "#ca8a04" },
  confirmed: { bg: "#dcfce7", color: "#16a34a" },
  cancelled: { bg: "#fee2e2", color: "#dc2626" },
  completed: { bg: "#e0f2fe", color: "#0369a1" },
};

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [visitModal, setVisitModal] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [saving, setSaving] = useState(false);
  const [visitForm, setVisitForm] = useState({
    complaint: "",
    diagnosis: "",
    prescription: [],
    tests_ordered: "",
    doctor_notes: "",
    next_visit_date: "",
    fee: "",
    doctor_id: ""
  });
  const [medInput, setMedInput] = useState({
    medicine: "", dosage: "", frequency: "", duration: ""
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchAppointments();
    fetchDoctors();
  }, [filter]);

  const fetchAppointments = async () => {
    try {
      const url = filter
        ? `/appointments/?status=${filter}`
        : "/appointments/";
      const res = await api.get(url);
      setAppointments(res.data);
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

  const updateStatus = async (id, status) => {
    try {
      await api.put(`/appointments/${id}`, { status });
      fetchAppointments();
    } catch (err) {
      console.error(err);
    }
  };

  const openVisitModal = (appointment) => {
    setVisitModal(appointment);
    setVisitForm({
      complaint: appointment.patient_concern || "",
      diagnosis: "",
      prescription: [],
      tests_ordered: "",
      doctor_notes: "",
      next_visit_date: "",
      fee: appointment.doctor_fee || "",
      doctor_id: appointment.doctor_id || ""
    });
  };

  const addMedicine = () => {
    if (!medInput.medicine) return;
    setVisitForm({
      ...visitForm,
      prescription: [...visitForm.prescription, { ...medInput }]
    });
    setMedInput({ medicine: "", dosage: "", frequency: "", duration: "" });
  };

  const removeMedicine = (index) => {
    setVisitForm({
      ...visitForm,
      prescription: visitForm.prescription.filter((_, i) => i !== index)
    });
  };

  const handleSaveVisit = async () => {
    setSaving(true);
    try {
      // Step 1 — Find or create patient
      let patientId = null;
      try {
        const lookupRes = await api.get(
          `/patients/lookup/${visitModal.patient_phone}`
        );
        patientId = lookupRes.data.id;
      } catch {
        // Patient not found — create them
        const createRes = await api.post("/patients/", {
          name: visitModal.patient_name,
          phone: visitModal.patient_phone,
        });
        patientId = createRes.data.patient_id;
      }

      // Step 2 — Save visit record
      await api.post("/visits/", {
        patient_id: patientId,
        doctor_id: visitForm.doctor_id || null,
        complaint: visitForm.complaint,
        diagnosis: visitForm.diagnosis,
        prescription: visitForm.prescription,
        tests_ordered: visitForm.tests_ordered,
        doctor_notes: visitForm.doctor_notes,
        next_visit_date: visitForm.next_visit_date || null,
        fee: visitForm.fee ? parseInt(visitForm.fee) : 0
      });

      // Step 3 — Mark appointment as completed
      await api.put(`/appointments/${visitModal.id}`, {
        status: "completed"
      });

      setVisitModal(null);
      fetchAppointments();
      alert("Visit saved successfully! Invoice created automatically.");
    } catch (err) {
      alert("Failed to save visit. Please try again.");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <div style={styles.topBar}>
          <h1 style={styles.heading}>Appointments</h1>
          <select
            style={styles.select}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        <div style={styles.tableCard}>
          {loading ? (
            <p>Loading...</p>
          ) : appointments.length === 0 ? (
            <p style={styles.empty}>No appointments found</p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  {[
                    "Patient", "Phone", "Concern",
                    "Doctor", "Slot", "Status", "Action"
                  ].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {appointments.map((a) => (
                  <tr key={a.id} style={styles.tr}>
                    <td style={styles.td}>{a.patient_name}</td>
                    <td style={styles.td}>{a.patient_phone}</td>
                    <td style={styles.td}>
                      {a.patient_concern
                        ? a.patient_concern.slice(0, 30) + "..."
                        : "-"}
                    </td>
                    <td style={styles.td}>{a.doctor_name}</td>
                    <td style={styles.td}>
                      {new Date(a.slot_datetime).toLocaleString()}
                    </td>
                    <td style={styles.td}>
                      <span style={{
                        ...styles.badge,
                        backgroundColor: STATUS_COLORS[a.status]?.bg || "#f3f4f6",
                        color: STATUS_COLORS[a.status]?.color || "#374151",
                      }}>
                        {a.status}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                        <select
                          style={styles.statusSelect}
                          value={a.status}
                          onChange={(e) => updateStatus(a.id, e.target.value)}
                        >
                          <option value="pending">Pending</option>
                          <option value="confirmed">Confirmed</option>
                          <option value="cancelled">Cancelled</option>
                          <option value="completed">Completed</option>
                        </select>
                        {a.status !== "cancelled" &&
                          a.status !== "completed" && (
                          <button
                            onClick={() => openVisitModal(a)}
                            style={styles.visitBtn}
                          >
                            🩺 Add Visit
                          </button>
                        )}
                        {a.status === "completed" && (
                          <button
                            onClick={() => navigate("/patients")}
                            style={styles.viewBtn}
                          >
                            View Record
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Visit Modal */}
      {visitModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <div>
                <h3 style={styles.modalTitle}>Record Visit</h3>
                <p style={styles.modalSub}>
                  {visitModal.patient_name} · {visitModal.patient_phone}
                </p>
              </div>
              <button
                onClick={() => setVisitModal(null)}
                style={styles.closeBtn}
              >
                ✕
              </button>
            </div>

            <div style={styles.modalBody}>
              <div style={styles.formGrid}>
                <div style={styles.field}>
                  <label style={styles.label}>Doctor</label>
                  <select
                    style={styles.input}
                    value={visitForm.doctor_id}
                    onChange={(e) => setVisitForm({
                      ...visitForm, doctor_id: e.target.value
                    })}
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
                  <label style={styles.label}>Fee (PKR)</label>
                  <input
                    type="number"
                    style={styles.input}
                    placeholder="e.g. 1000"
                    value={visitForm.fee}
                    onChange={(e) => setVisitForm({
                      ...visitForm, fee: e.target.value
                    })}
                  />
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Complaint</label>
                <textarea
                  style={styles.textarea}
                  value={visitForm.complaint}
                  onChange={(e) => setVisitForm({
                    ...visitForm, complaint: e.target.value
                  })}
                  placeholder="Patient's complaint"
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Diagnosis</label>
                <textarea
                  style={styles.textarea}
                  value={visitForm.diagnosis}
                  onChange={(e) => setVisitForm({
                    ...visitForm, diagnosis: e.target.value
                  })}
                  placeholder="Doctor's diagnosis"
                />
              </div>

              {/* Prescription */}
              <div style={styles.field}>
                <label style={styles.label}>Prescription</label>
                <div style={styles.medRow}>
                  <input
                    style={{ ...styles.input, flex: 2 }}
                    placeholder="Medicine"
                    value={medInput.medicine}
                    onChange={(e) => setMedInput({
                      ...medInput, medicine: e.target.value
                    })}
                  />
                  <input
                    style={{ ...styles.input, flex: 1 }}
                    placeholder="Dosage"
                    value={medInput.dosage}
                    onChange={(e) => setMedInput({
                      ...medInput, dosage: e.target.value
                    })}
                  />
                  <input
                    style={{ ...styles.input, flex: 1 }}
                    placeholder="Frequency"
                    value={medInput.frequency}
                    onChange={(e) => setMedInput({
                      ...medInput, frequency: e.target.value
                    })}
                  />
                  <input
                    style={{ ...styles.input, flex: 1 }}
                    placeholder="Duration"
                    value={medInput.duration}
                    onChange={(e) => setMedInput({
                      ...medInput, duration: e.target.value
                    })}
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
                        <span>
                          <strong>{med.medicine}</strong>
                          <span style={{ color: "#64748b", marginLeft: "8px", fontSize: "12px" }}>
                            {med.dosage} · {med.frequency} · {med.duration}
                          </span>
                        </span>
                        <button
                          onClick={() => removeMedicine(i)}
                          style={styles.removeMedBtn}
                        >
                          ✕
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
                    placeholder="e.g. CBC, Blood Sugar"
                    value={visitForm.tests_ordered}
                    onChange={(e) => setVisitForm({
                      ...visitForm, tests_ordered: e.target.value
                    })}
                  />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Next Visit Date</label>
                  <input
                    type="date"
                    style={styles.input}
                    value={visitForm.next_visit_date}
                    onChange={(e) => setVisitForm({
                      ...visitForm, next_visit_date: e.target.value
                    })}
                  />
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Doctor Notes (Private)</label>
                <textarea
                  style={styles.textarea}
                  placeholder="Private notes — not visible to patient"
                  value={visitForm.doctor_notes}
                  onChange={(e) => setVisitForm({
                    ...visitForm, doctor_notes: e.target.value
                  })}
                />
              </div>
            </div>

            <div style={styles.modalFooter}>
              <button
                onClick={handleSaveVisit}
                style={saving ? styles.savingBtn : styles.saveBtn}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Visit + Create Invoice"}
              </button>
              <button
                onClick={() => setVisitModal(null)}
                style={styles.cancelBtn}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  layout: { display: "flex", minHeight: "100vh", backgroundColor: "#f8fafc" },
  main: { marginLeft: "240px", padding: "32px", flex: 1 },
  topBar: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: "24px"
  },
  heading: { fontSize: "24px", fontWeight: "700", color: "#1e293b", margin: 0 },
  select: {
    padding: "10px 12px", borderRadius: "8px",
    border: "1px solid #d1d5db", fontSize: "14px",
    outline: "none", cursor: "pointer"
  },
  tableCard: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    overflowX: "auto"
  },
  empty: { color: "#9ca3af", fontSize: "14px" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: {
    textAlign: "left", padding: "12px", fontSize: "12px",
    fontWeight: "600", color: "#6b7280",
    borderBottom: "1px solid #e5e7eb",
    textTransform: "uppercase", whiteSpace: "nowrap"
  },
  tr: { borderBottom: "1px solid #f3f4f6" },
  td: { padding: "12px", fontSize: "14px", color: "#374151", verticalAlign: "middle" },
  badge: {
    padding: "4px 10px", borderRadius: "20px",
    fontSize: "12px", fontWeight: "600"
  },
  statusSelect: {
    padding: "6px 8px", borderRadius: "6px",
    border: "1px solid #d1d5db", fontSize: "13px",
    cursor: "pointer", outline: "none"
  },
  visitBtn: {
    backgroundColor: "#eff6ff", color: "#2563eb",
    border: "none", padding: "6px 10px",
    borderRadius: "6px", cursor: "pointer",
    fontWeight: "600", fontSize: "12px",
    whiteSpace: "nowrap"
  },
  viewBtn: {
    backgroundColor: "#f0fdf4", color: "#16a34a",
    border: "none", padding: "6px 10px",
    borderRadius: "6px", cursor: "pointer",
    fontWeight: "600", fontSize: "12px",
    whiteSpace: "nowrap"
  },
  modalOverlay: {
    position: "fixed", top: 0, left: 0,
    right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex", alignItems: "center",
    justifyContent: "center", zIndex: 1000,
    padding: "20px"
  },
  modal: {
    backgroundColor: "#fff", borderRadius: "16px",
    width: "100%", maxWidth: "680px",
    maxHeight: "90vh", overflow: "hidden",
    display: "flex", flexDirection: "column",
    boxShadow: "0 20px 60px rgba(0,0,0,0.2)"
  },
  modalHeader: {
    display: "flex", justifyContent: "space-between",
    alignItems: "flex-start", padding: "20px 24px",
    borderBottom: "1px solid #e5e7eb"
  },
  modalTitle: {
    fontSize: "18px", fontWeight: "700",
    color: "#1e293b", margin: "0 0 4px 0"
  },
  modalSub: { fontSize: "13px", color: "#64748b", margin: 0 },
  closeBtn: {
    backgroundColor: "#f1f5f9", border: "none",
    borderRadius: "6px", padding: "6px 10px",
    cursor: "pointer", fontSize: "14px", color: "#64748b"
  },
  modalBody: {
    padding: "20px 24px", overflowY: "auto",
    flex: 1, display: "flex",
    flexDirection: "column", gap: "14px"
  },
  modalFooter: {
    padding: "16px 24px", borderTop: "1px solid #e5e7eb",
    display: "flex", gap: "12px"
  },
  saveBtn: {
    backgroundColor: "#2563eb", color: "#fff",
    border: "none", padding: "12px 24px",
    borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px", flex: 1
  },
  savingBtn: {
    backgroundColor: "#93c5fd", color: "#fff",
    border: "none", padding: "12px 24px",
    borderRadius: "8px", cursor: "not-allowed",
    fontWeight: "600", fontSize: "14px", flex: 1
  },
  cancelBtn: {
    backgroundColor: "#f1f5f9", color: "#374151",
    border: "none", padding: "12px 24px",
    borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px"
  },
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
    outline: "none", resize: "vertical", minHeight: "70px"
  },
  medRow: { display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" },
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
    border: "1px solid #e2e8f0", fontSize: "13px"
  },
  removeMedBtn: {
    backgroundColor: "#fee2e2", color: "#dc2626",
    border: "none", padding: "3px 7px",
    borderRadius: "4px", cursor: "pointer", fontSize: "12px"
  },
};