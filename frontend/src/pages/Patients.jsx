import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { useNavigate } from "react-router-dom";
import { Plus, Search, User } from "lucide-react";

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "", phone: "", age: "",
    gender: "", blood_group: "",
    allergies: "", chronic_conditions: "",
    emergency_contact: ""
  });

  useEffect(() => {
    fetchPatients();
  }, [search]);

  const fetchPatients = async () => {
    try {
      const url = search
        ? `/patients/?search=${search}`
        : "/patients/";
      const res = await api.get(url);
      setPatients(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setForm({
      name: "", phone: "", age: "",
      gender: "", blood_group: "",
      allergies: "", chronic_conditions: "",
      emergency_contact: ""
    });
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/patients/", {
        ...form,
        age: form.age ? parseInt(form.age) : null
      });
      resetForm();
      setShowForm(false);
      fetchPatients();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to add patient"
      );
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>

        <div style={styles.topBar}>
          <h1 style={styles.heading}>Patients</h1>
          <button
            onClick={() => setShowForm(!showForm)}
            style={styles.addButton}
          >
            <Plus size={16} />
            Add Patient
          </button>
        </div>

        {showForm && (
          <div style={styles.formCard}>
            <h3 style={styles.formTitle}>Add New Patient</h3>
            {error && <p style={styles.error}>{error}</p>}
            <form onSubmit={handleAdd} style={styles.form}>
              <div style={styles.formGrid}>
                <input
                  style={styles.input}
                  placeholder="Full Name *"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
                <input
                  style={styles.input}
                  placeholder="Phone Number *"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  required
                />
                <input
                  style={styles.input}
                  placeholder="Age"
                  type="number"
                  value={form.age}
                  onChange={(e) => setForm({ ...form, age: e.target.value })}
                />
                <select
                  style={styles.input}
                  value={form.gender}
                  onChange={(e) => setForm({ ...form, gender: e.target.value })}
                >
                  <option value="">Select Gender</option>
                  <option>Male</option>
                  <option>Female</option>
                  <option>Other</option>
                </select>
                <select
                  style={styles.input}
                  value={form.blood_group}
                  onChange={(e) => setForm({ ...form, blood_group: e.target.value })}
                >
                  <option value="">Blood Group</option>
                  {["A+","A-","B+","B-","AB+","AB-","O+","O-"].map(b => (
                    <option key={b}>{b}</option>
                  ))}
                </select>
                <input
                  style={styles.input}
                  placeholder="Emergency Contact"
                  value={form.emergency_contact}
                  onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })}
                />
              </div>
              <input
                style={styles.input}
                placeholder="Allergies (e.g. Penicillin, Aspirin)"
                value={form.allergies}
                onChange={(e) => setForm({ ...form, allergies: e.target.value })}
              />
              <input
                style={styles.input}
                placeholder="Chronic Conditions (e.g. Diabetes, Hypertension)"
                value={form.chronic_conditions}
                onChange={(e) => setForm({ ...form, chronic_conditions: e.target.value })}
              />
              <div style={styles.formButtons}>
                <button type="submit" style={styles.submitButton}>
                  Save Patient
                </button>
                <button
                  type="button"
                  onClick={() => { resetForm(); setShowForm(false); }}
                  style={styles.cancelButton}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div style={styles.searchBar}>
          <Search size={16} color="#94a3b8" />
          <input
            style={styles.searchInput}
            placeholder="Search by name or phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div style={styles.tableCard}>
          {loading ? (
            <p>Loading...</p>
          ) : patients.length === 0 ? (
            <p style={styles.empty}>
              No patients found. Add your first patient above.
            </p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Name", "Phone", "Age", "Gender",
                    "Blood Group", "Conditions", "Visits", "Action"].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <tr key={p.id} style={styles.tr}>
                    <td style={styles.td}>
                      <div style={styles.nameCell}>
                        <div style={styles.avatar}>
                          {p.name.charAt(0).toUpperCase()}
                        </div>
                        <strong>{p.name}</strong>
                      </div>
                    </td>
                    <td style={styles.td}>{p.phone}</td>
                    <td style={styles.td}>{p.age || "-"}</td>
                    <td style={styles.td}>{p.gender || "-"}</td>
                    <td style={styles.td}>
                      {p.blood_group ? (
                        <span style={styles.bloodBadge}>
                          {p.blood_group}
                        </span>
                      ) : "-"}
                    </td>
                    <td style={styles.td}>
                      {p.chronic_conditions
                        ? p.chronic_conditions.slice(0, 30) + "..."
                        : "-"}
                    </td>
                    <td style={styles.td}>
                      <span style={styles.visitBadge}>
                        {p.total_visits} visits
                      </span>
                    </td>
                    <td style={styles.td}>
                      <button
                        onClick={() => navigate(`/patients/${p.id}`)}
                        style={styles.viewButton}
                      >
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
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
  formTitle: {
    fontSize: "16px", fontWeight: "600",
    marginBottom: "16px", color: "#1e293b"
  },
  error: { color: "#dc2626", fontSize: "14px", marginBottom: "12px" },
  form: { display: "flex", flexDirection: "column", gap: "12px" },
  formGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" },
  input: {
    padding: "10px 12px", borderRadius: "8px",
    border: "1px solid #d1d5db", fontSize: "14px",
    outline: "none", width: "100%", boxSizing: "border-box"
  },
  formButtons: { display: "flex", gap: "12px" },
  submitButton: {
    backgroundColor: "#2563eb", color: "#fff", border: "none",
    padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px"
  },
  cancelButton: {
    backgroundColor: "#f1f5f9", color: "#374151", border: "none",
    padding: "10px 20px", borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "14px"
  },
  searchBar: {
    display: "flex", alignItems: "center", gap: "10px",
    backgroundColor: "#fff", borderRadius: "10px",
    padding: "10px 16px", marginBottom: "16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    border: "1px solid #e2e8f0"
  },
  searchInput: {
    border: "none", outline: "none", fontSize: "14px",
    flex: 1, backgroundColor: "transparent"
  },
  tableCard: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    overflowX: "auto"
  },
  empty: { color: "#9ca3af", fontSize: "14px" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: {
    textAlign: "left", padding: "12px", fontSize: "11px",
    fontWeight: "700", color: "#6b7280",
    borderBottom: "1px solid #e5e7eb",
    textTransform: "uppercase", whiteSpace: "nowrap"
  },
  tr: { borderBottom: "1px solid #f3f4f6" },
  td: { padding: "12px", fontSize: "14px", color: "#374151", verticalAlign: "middle" },
  nameCell: { display: "flex", alignItems: "center", gap: "10px" },
  avatar: {
    width: "34px", height: "34px", borderRadius: "50%",
    backgroundColor: "#eff6ff", color: "#2563eb",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontWeight: "700", fontSize: "14px", flexShrink: 0
  },
  bloodBadge: {
    backgroundColor: "#fee2e2", color: "#dc2626",
    padding: "2px 8px", borderRadius: "12px",
    fontSize: "12px", fontWeight: "600"
  },
  visitBadge: {
    backgroundColor: "#eff6ff", color: "#2563eb",
    padding: "2px 8px", borderRadius: "12px",
    fontSize: "12px", fontWeight: "600"
  },
  viewButton: {
    backgroundColor: "#f1f5f9", color: "#2563eb",
    border: "none", padding: "6px 12px",
    borderRadius: "6px", cursor: "pointer",
    fontWeight: "600", fontSize: "13px"
  },
};