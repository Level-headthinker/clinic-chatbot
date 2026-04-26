import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";

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

  useEffect(() => {
    fetchAppointments();
  }, [filter]);

  const fetchAppointments = async () => {
    try {
      const url = filter ? `/appointments/?status=${filter}` : "/appointments/";
      const res = await api.get(url);
      setAppointments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
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
                    "Patient",
                    "Phone",
                    "Concern",
                    "Doctor",
                    "Slot",
                    "Status",
                    "Action",
                  ].map((h) => (
                    <th key={h} style={styles.th}>
                      {h}
                    </th>
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
                        ? a.patient_concern.slice(0, 40) + "..."
                        : "-"}
                    </td>
                    <td style={styles.td}>{a.doctor_name}</td>
                    <td style={styles.td}>
                      {new Date(a.slot_datetime).toLocaleString()}
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.badge,
                          backgroundColor:
                            STATUS_COLORS[a.status]?.bg || "#f3f4f6",
                          color:
                            STATUS_COLORS[a.status]?.color || "#374151",
                        }}
                      >
                        {a.status}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <select
                        style={styles.statusSelect}
                        value={a.status}
                        onChange={(e) =>
                          updateStatus(a.id, e.target.value)
                        }
                      >
                        <option value="pending">Pending</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="cancelled">Cancelled</option>
                        <option value="completed">Completed</option>
                      </select>
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
  heading: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#1e293b",
    margin: 0,
  },
  select: {
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
    cursor: "pointer",
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
  statusSelect: {
    padding: "6px 8px",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    fontSize: "13px",
    cursor: "pointer",
    outline: "none",
  },
};