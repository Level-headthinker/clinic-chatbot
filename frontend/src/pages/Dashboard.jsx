import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { Calendar, Users, TrendingUp, Clock } from "lucide-react";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, apptRes] = await Promise.all([
        api.get("/leads/stats"),
        api.get("/appointments/"),
      ]);
      setStats(statsRes.data);
      setAppointments(apptRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <h1 style={styles.heading}>Dashboard</h1>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <>
            <div style={styles.grid}>
              <StatCard
                icon={<Users size={24} color="#2563eb" />}
                label="Total Leads"
                value={stats?.total || 0}
                bg="#eff6ff"
              />
              <StatCard
                icon={<Clock size={24} color="#f59e0b" />}
                label="New Leads"
                value={stats?.new || 0}
                bg="#fffbeb"
              />
              <StatCard
                icon={<Calendar size={24} color="#10b981" />}
                label="Appointments"
                value={appointments.length}
                bg="#ecfdf5"
              />
              <StatCard
                icon={<TrendingUp size={24} color="#8b5cf6" />}
                label="Conversion Rate"
                value={stats?.conversion_rate || "0%"}
                bg="#f5f3ff"
              />
            </div>

            <div style={styles.section}>
              <h2 style={styles.sectionTitle}>Recent Appointments</h2>
              {appointments.length === 0 ? (
                <p style={styles.empty}>No appointments yet</p>
              ) : (
                <table style={styles.table}>
                  <thead>
                    <tr>
                      {["Patient", "Phone", "Doctor", "Slot", "Status"].map(
                        (h) => (
                          <th key={h} style={styles.th}>
                            {h}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {appointments.map((a) => (
                      <tr key={a.id} style={styles.tr}>
                        <td style={styles.td}>{a.patient_name}</td>
                        <td style={styles.td}>{a.patient_phone}</td>
                        <td style={styles.td}>{a.doctor_name}</td>
                        <td style={styles.td}>
                          {new Date(a.slot_datetime).toLocaleString()}
                        </td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.badge,
                              backgroundColor:
                                a.status === "confirmed"
                                  ? "#dcfce7"
                                  : a.status === "cancelled"
                                  ? "#fee2e2"
                                  : "#fef9c3",
                              color:
                                a.status === "confirmed"
                                  ? "#16a34a"
                                  : a.status === "cancelled"
                                  ? "#dc2626"
                                  : "#ca8a04",
                            }}
                          >
                            {a.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, bg }) {
  return (
    <div style={{ ...styles.card, backgroundColor: bg }}>
      <div style={styles.cardIcon}>{icon}</div>
      <div>
        <p style={styles.cardLabel}>{label}</p>
        <p style={styles.cardValue}>{value}</p>
      </div>
    </div>
  );
}

const styles = {
  layout: {
    display: "flex",
    minHeight: "100vh",
    backgroundColor: "#f8fafc",
  },
  main: {
    marginLeft: "240px",
    padding: "32px",
    flex: 1,
  },
  heading: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#1e293b",
    marginBottom: "24px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "16px",
    marginBottom: "32px",
  },
  card: {
    borderRadius: "12px",
    padding: "20px",
    display: "flex",
    alignItems: "center",
    gap: "16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  cardIcon: {
    padding: "12px",
    borderRadius: "10px",
    backgroundColor: "#ffffff",
  },
  cardLabel: {
    fontSize: "12px",
    color: "#6b7280",
    margin: "0 0 4px 0",
  },
  cardValue: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#1e293b",
    margin: 0,
  },
  section: {
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    padding: "24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  sectionTitle: {
    fontSize: "16px",
    fontWeight: "600",
    color: "#1e293b",
    marginBottom: "16px",
  },
  empty: {
    color: "#9ca3af",
    fontSize: "14px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  th: {
    textAlign: "left",
    padding: "12px",
    fontSize: "12px",
    fontWeight: "600",
    color: "#6b7280",
    borderBottom: "1px solid #e5e7eb",
    textTransform: "uppercase",
  },
  tr: {
    borderBottom: "1px solid #f3f4f6",
  },
  td: {
    padding: "12px",
    fontSize: "14px",
    color: "#374151",
  },
  badge: {
    padding: "4px 10px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: "600",
  },
};