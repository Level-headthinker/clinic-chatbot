import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { Plus, Trash2 } from "lucide-react";

export default function Doctors() {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    specialty: "",
    qualification: "",
    fee: "",
    bio: "",
  });

  useEffect(() => {
    fetchDoctors();
  }, []);

  const fetchDoctors = async () => {
    try {
      const res = await api.get("/doctors/");
      setDoctors(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/doctors/", {
        ...form,
        available_slots: [],
      });
      setForm({
        name: "",
        specialty: "",
        qualification: "",
        fee: "",
        bio: "",
      });
      setShowForm(false);
      fetchDoctors();
    } catch (err) {
      setError("Failed to add doctor");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Remove this doctor?")) return;
    try {
      await api.delete(`/doctors/${id}`);
      fetchDoctors();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <div style={styles.topBar}>
          <h1 style={styles.heading}>Doctors</h1>
          <button
            onClick={() => setShowForm(!showForm)}
            style={styles.addButton}
          >
            <Plus size={16} />
            Add Doctor
          </button>
        </div>

        {showForm && (
          <div style={styles.formCard}>
            <h3 style={styles.formTitle}>Add New Doctor</h3>
            {error && <p style={styles.error}>{error}</p>}
            <form onSubmit={handleAdd} style={styles.form}>
              <div style={styles.formGrid}>
                <input
                  style={styles.input}
                  placeholder="Full Name"
                  value={form.name}
                  onChange={(e) =>
                    setForm({ ...form, name: e.target.value })
                  }
                  required
                />
                <input
                  style={styles.input}
                  placeholder="Specialty (e.g. Cardiologist)"
                  value={form.specialty}
                  onChange={(e) =>
                    setForm({ ...form, specialty: e.target.value })
                  }
                  required
                />
                <input
                  style={styles.input}
                  placeholder="Qualification (e.g. MBBS, FCPS)"
                  value={form.qualification}
                  onChange={(e) =>
                    setForm({ ...form, qualification: e.target.value })
                  }
                />
                <input
                  style={styles.input}
                  placeholder="Fee (e.g. 1500 PKR)"
                  value={form.fee}
                  onChange={(e) =>
                    setForm({ ...form, fee: e.target.value })
                  }
                />
              </div>
              <textarea
                style={styles.textarea}
                placeholder="Short bio (optional)"
                value={form.bio}
                onChange={(e) =>
                  setForm({ ...form, bio: e.target.value })
                }
              />
              <div style={styles.formButtons}>
                <button type="submit" style={styles.submitButton}>
                  Save Doctor
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  style={styles.cancelButton}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div style={styles.tableCard}>
          {loading ? (
            <p>Loading...</p>
          ) : doctors.length === 0 ? (
            <p style={styles.empty}>
              No doctors added yet. Click Add Doctor to start.
            </p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Name", "Specialty", "Qualification", "Fee", "Status", "Action"].map(
                    (h) => (
                      <th key={h} style={styles.th}>
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {doctors.map((d) => (
                  <tr key={d.id} style={styles.tr}>
                    <td style={styles.td}>Dr. {d.name}</td>
                    <td style={styles.td}>{d.specialty}</td>
                    <td style={styles.td}>{d.qualification || "-"}</td>
                    <td style={styles.td}>{d.fee || "-"}</td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.badge,
                          backgroundColor: d.is_active
                            ? "#dcfce7"
                            : "#fee2e2",
                          color: d.is_active ? "#16a34a" : "#dc2626",
                        }}
                      >
                        {d.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <button
                        onClick={() => handleDelete(d.id)}
                        style={styles.deleteButton}
                      >
                        <Trash2 size={14} />
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
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "24px",
  },
  heading: { fontSize: "24px", fontWeight: "700", color: "#1e293b", margin: 0 },
  addButton: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    backgroundColor: "#2563eb",
    color: "#fff",
    border: "none",
    padding: "10px 16px",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "600",
    fontSize: "14px",
  },
  formCard: {
    backgroundColor: "#fff",
    borderRadius: "12px",
    padding: "24px",
    marginBottom: "24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  formTitle: { fontSize: "16px", fontWeight: "600", marginBottom: "16px" },
  error: { color: "#dc2626", fontSize: "14px", marginBottom: "12px" },
  form: { display: "flex", flexDirection: "column", gap: "12px" },
  formGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "12px",
  },
  input: {
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
  },
  textarea: {
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
    resize: "vertical",
    minHeight: "80px",
  },
  formButtons: { display: "flex", gap: "12px" },
  submitButton: {
    backgroundColor: "#2563eb",
    color: "#fff",
    border: "none",
    padding: "10px 20px",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "600",
    fontSize: "14px",
  },
  cancelButton: {
    backgroundColor: "#f1f5f9",
    color: "#374151",
    border: "none",
    padding: "10px 20px",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "600",
    fontSize: "14px",
  },
  tableCard: {
    backgroundColor: "#fff",
    borderRadius: "12px",
    padding: "24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  empty: { color: "#9ca3af", fontSize: "14px" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: {
    textAlign: "left",
    padding: "12px",
    fontSize: "12px",
    fontWeight: "600",
    color: "#6b7280",
    borderBottom: "1px solid #e5e7eb",
    textTransform: "uppercase",
  },
  tr: { borderBottom: "1px solid #f3f4f6" },
  td: { padding: "12px", fontSize: "14px", color: "#374151" },
  badge: {
    padding: "4px 10px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: "600",
  },
  deleteButton: {
    backgroundColor: "#fee2e2",
    color: "#dc2626",
    border: "none",
    padding: "6px 8px",
    borderRadius: "6px",
    cursor: "pointer",
  },
};