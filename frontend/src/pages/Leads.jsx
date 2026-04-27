import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";

const STATUS_COLORS = {
  new: { bg: "#eff6ff", color: "#2563eb" },
  contacted: { bg: "#fef9c3", color: "#ca8a04" },
  converted: { bg: "#dcfce7", color: "#16a34a" },
  lost: { bg: "#fee2e2", color: "#dc2626" },
};

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [filter]);

  const fetchLeads = async () => {
    try {
      const url = filter ? `/leads/?status=${filter}` : "/leads/";
      const res = await api.get(url);
      setLeads(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await api.get("/leads/stats");
      setStats(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await api.put(`/leads/${id}`, { status });
      fetchLeads();
      fetchStats();
    } catch (err) {
      console.error(err);
    }
  };

  const deleteLead = async (id) => {
    if (!window.confirm("Remove this lead?")) return;
    try {
      await api.delete(`/leads/${id}`);
      fetchLeads();
    } catch (err) {
      console.error(err);
    }
  };
  const openWhatsApp = (phone, name) => {
  const message = encodeURIComponent(
    `Assalam o Alaikum ${name} ji, City Clinic ki taraf se message hai. ` +
    `Aap ne hamare chatbot se appointment ki inquiry ki thi. ` +
    `Kya aap appointment book karna chahte hain? ` +
    `Humara number hai, reply karein ya call karein. Shukriya!`
  );
  window.open(`https://wa.me/${phone}?text=${message}`, "_blank");
};

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <div style={styles.topBar}>
          <h1 style={styles.heading}>Leads</h1>
          <select
            style={styles.select}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">All Leads</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>
        </div>

        {stats && (
          <div style={styles.statsRow}>
            {[
              { label: "Total", value: stats.total, color: "#2563eb" },
              { label: "New", value: stats.new, color: "#f59e0b" },
              { label: "Contacted", value: stats.contacted, color: "#8b5cf6" },
              { label: "Converted", value: stats.converted, color: "#10b981" },
              { label: "Rate", value: stats.conversion_rate, color: "#10b981" },
            ].map((s) => (
              <div key={s.label} style={styles.statBox}>
                <p style={styles.statLabel}>{s.label}</p>
                <p style={{ ...styles.statValue, color: s.color }}>
                  {s.value}
                </p>
              </div>
            ))}
          </div>
        )}

        <div style={styles.tableCard}>
          {loading ? (
            <p>Loading...</p>
          ) : leads.length === 0 ? (
            <p style={styles.empty}>No leads found</p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Name", "Phone", "Concern", "Status", "Date", "Action"].map(
                    (h) => (
                      <th key={h} style={styles.th}>
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => (
                  <tr key={l.id} style={styles.tr}>
                    <td style={styles.td}>{l.name}</td>
                    <td style={styles.td}>{l.phone}</td>
                    <td style={styles.td}>
                      {l.concern
                        ? l.concern.slice(0, 50) + "..."
                        : "-"}
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.badge,
                          backgroundColor:
                            STATUS_COLORS[l.status]?.bg || "#f3f4f6",
                          color:
                            STATUS_COLORS[l.status]?.color || "#374151",
                        }}
                      >
                        {l.status}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {new Date(l.created_at).toLocaleDateString()}
                    </td>
                    <td style={styles.td} style={{ display: "flex", gap: "8px" }}>
                      <select
                        style={styles.statusSelect}
                        value={l.status}
                        onChange={(e) => updateStatus(l.id, e.target.value)}
                      >
                        <option value="new">New</option>
                        <option value="contacted">Contacted</option>
                        <option value="converted">Converted</option>
                        <option value="lost">Lost</option>
                      </select>
                      <button
                        onClick={() => openWhatsApp(l.phone, l.name)}
                        style={styles.whatsappButton}
                        title="Send WhatsApp"
                      >
                        💬
                      </button>
                      <button
                        onClick={() => deleteLead(l.id)}
                        style={styles.deleteButton}
                      >
                        ✕
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
  select: {
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
    cursor: "pointer",
  },
  statsRow: {
    display: "flex",
    gap: "16px",
    marginBottom: "24px",
  },
  statBox: {
    backgroundColor: "#fff",
    borderRadius: "10px",
    padding: "16px 24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    minWidth: "100px",
    textAlign: "center",
  },
  statLabel: {
    fontSize: "12px",
    color: "#6b7280",
    margin: "0 0 4px 0",
    textTransform: "uppercase",
  },
  statValue: {
    fontSize: "22px",
    fontWeight: "700",
    margin: 0,
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
  deleteButton: {
    backgroundColor: "#fee2e2",
    color: "#dc2626",
    border: "none",
    padding: "6px 10px",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: "700",
  },
  whatsappButton: {
  backgroundColor: "#dcfce7",
  color: "#16a34a",
  border: "none",
  padding: "6px 10px",
  borderRadius: "6px",
  cursor: "pointer",
  fontWeight: "700",
  fontSize: "16px",
},
};