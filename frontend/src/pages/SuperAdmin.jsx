import { useState, useEffect } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import {
  Users, Calendar, TrendingUp,
  MessageSquare, Stethoscope, DollarSign
} from "lucide-react";

const SUPER_ADMIN_EMAIL = "admin@cityclinic.com";

export default function SuperAdmin() {
  const [stats, setStats] = useState(null);
  const [clinics, setClinics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user || user.email !== SUPER_ADMIN_EMAIL) {
      navigate("/login");
      return;
    }
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, clinicsRes] = await Promise.all([
        api.get("/super/stats"),
        api.get("/super/clinics"),
      ]);
      setStats(statsRes.data);
      setClinics(clinicsRes.data);
    } catch (err) {
      setError("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const toggleClinic = async (id, name) => {
    if (!window.confirm(`Toggle status for ${name}?`)) return;
    try {
      await api.put(`/super/clinics/${id}/toggle`);
      fetchData();
    } catch (err) {
      alert("Failed to update clinic");
    }
  };

  const updatePlan = async (id, plan) => {
    try {
      await api.put(`/super/clinics/${id}/plan?plan=${plan}`);
      fetchData();
    } catch (err) {
      alert("Failed to update plan");
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (loading) return (
    <div style={styles.loadingScreen}>
      <p>Loading Super Admin...</p>
    </div>
  );

  return (
    <div style={styles.layout}>

      {/* Sidebar */}
      <div style={styles.sidebar}>
        <div style={styles.logoArea}>
          <h2 style={styles.logo}>🏥 ClinicBot</h2>
          <p style={styles.superLabel}>⚡ Super Admin</p>
        </div>
        <div style={styles.sidebarLinks}>
          <div style={styles.sidebarLink}>📊 Overview</div>
          <div style={styles.sidebarLink}>🏥 All Clinics</div>
        </div>
        <button onClick={handleLogout} style={styles.logoutBtn}>
          🚪 Logout
        </button>
      </div>

      {/* Main */}
      <div style={styles.main}>
        <div style={styles.topBar}>
          <h1 style={styles.heading}>Platform Overview</h1>
          <span style={styles.badge}>Super Admin</span>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        {/* Stats Grid */}
        {stats && (
          <div style={styles.statsGrid}>
            {[
              { icon: <Users size={22} color="#2563eb" />, label: "Total Clinics", value: stats.total_clinics, bg: "#eff6ff" },
              { icon: <Calendar size={22} color="#10b981" />, label: "Appointments", value: stats.total_appointments, bg: "#ecfdf5" },
              { icon: <Users size={22} color="#f59e0b" />, label: "Total Leads", value: stats.total_leads, bg: "#fffbeb" },
              { icon: <Stethoscope size={22} color="#8b5cf6" />, label: "Doctors", value: stats.total_doctors, bg: "#f5f3ff" },
              { icon: <MessageSquare size={22} color="#0d9488" />, label: "Chat Sessions", value: stats.total_chats, bg: "#f0fdfa" },
              { icon: <DollarSign size={22} color="#16a34a" />, label: "Est. MRR (PKR)", value: stats.estimated_mrr.toLocaleString(), bg: "#f0fdf4" },
            ].map((s, i) => (
              <div key={i} style={{ ...styles.statCard, backgroundColor: s.bg }}>
                <div style={styles.statIcon}>{s.icon}</div>
                <div>
                  <p style={styles.statLabel}>{s.label}</p>
                  <p style={styles.statValue}>{s.value}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Revenue Banner */}
        {stats && (
          <div style={styles.revenueBanner}>
            <div>
              <p style={styles.revenueLabel}>Estimated Monthly Revenue</p>
              <p style={styles.revenueValue}>
                PKR {stats.estimated_mrr.toLocaleString()}
              </p>
            </div>
            <div style={styles.revenueDivider} />
            <div>
              <p style={styles.revenueLabel}>Estimated Annual Revenue</p>
              <p style={styles.revenueValue}>
                PKR {stats.estimated_arr.toLocaleString()}
              </p>
            </div>
            <div style={styles.revenueDivider} />
            <div>
              <p style={styles.revenueLabel}>Per Clinic Rate</p>
              <p style={styles.revenueValue}>PKR 3,000/mo</p>
            </div>
          </div>
        )}

        {/* Clinics Table */}
        <div style={styles.tableCard}>
          <h2 style={styles.tableTitle}>
            All Clinics ({clinics.length})
          </h2>
          <div style={{ overflowX: "auto" }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Clinic", "Slug", "Plan", "Doctors", "Leads", "Appts", "Chats", "Status", "Joined", "Actions"].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {clinics.map((c) => (
                  <tr key={c.id} style={styles.tr}>
                    <td style={{ ...styles.td, fontWeight: "600", color: "#1e293b" }}>
                      {c.name}
                    </td>
                    <td style={styles.td}>
                      <code style={styles.slugCode}>{c.slug}</code>
                    </td>
                    <td style={styles.td}>
                      <select
                        style={styles.planSelect}
                        value={c.plan}
                        onChange={(e) => updatePlan(c.id, e.target.value)}
                      >
                        <option value="starter">Starter</option>
                        <option value="growth">Growth</option>
                        <option value="enterprise">Enterprise</option>
                      </select>
                    </td>
                    <td style={{ ...styles.td, textAlign: "center" }}>{c.doctors}</td>
                    <td style={{ ...styles.td, textAlign: "center" }}>{c.leads}</td>
                    <td style={{ ...styles.td, textAlign: "center" }}>{c.appointments}</td>
                    <td style={{ ...styles.td, textAlign: "center" }}>{c.chats}</td>
                    <td style={styles.td}>
                      <span style={{
                        ...styles.statusBadge,
                        backgroundColor: c.is_active ? "#dcfce7" : "#fee2e2",
                        color: c.is_active ? "#16a34a" : "#dc2626",
                      }}>
                        {c.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td style={styles.td}>
                      <button
                        onClick={() => toggleClinic(c.id, c.name)}
                        style={{
                          ...styles.toggleBtn,
                          backgroundColor: c.is_active ? "#fee2e2" : "#dcfce7",
                          color: c.is_active ? "#dc2626" : "#16a34a",
                        }}
                      >
                        {c.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  loadingScreen: {
    display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "100vh", fontSize: "16px", color: "#64748b"
  },
  layout: { display: "flex", minHeight: "100vh", backgroundColor: "#f8fafc" },
  sidebar: {
    width: "220px", minHeight: "100vh", backgroundColor: "#0f2247",
    display: "flex", flexDirection: "column", padding: "24px 16px",
    position: "fixed", top: 0, left: 0,
  },
  logoArea: { marginBottom: "32px", paddingBottom: "20px", borderBottom: "1px solid #1e3a5f" },
  logo: { color: "#ffffff", fontSize: "18px", fontWeight: "700", margin: "0 0 4px 0" },
  superLabel: { color: "#fbbf24", fontSize: "11px", fontWeight: "700", margin: 0, letterSpacing: "1px" },
  sidebarLinks: { flex: 1, display: "flex", flexDirection: "column", gap: "4px" },
  sidebarLink: {
    padding: "10px 14px", borderRadius: "8px", color: "#93c5fd",
    fontSize: "13px", cursor: "pointer", backgroundColor: "#1e3a5f"
  },
  logoutBtn: {
    backgroundColor: "transparent", color: "#f87171", border: "none",
    padding: "10px 14px", borderRadius: "8px", cursor: "pointer",
    fontSize: "13px", textAlign: "left", width: "100%"
  },
  main: { marginLeft: "220px", padding: "32px", flex: 1 },
  topBar: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: "24px"
  },
  heading: { fontSize: "24px", fontWeight: "700", color: "#1e293b", margin: 0 },
  badge: {
    backgroundColor: "#fef9c3", color: "#ca8a04", padding: "6px 14px",
    borderRadius: "20px", fontSize: "12px", fontWeight: "700"
  },
  error: {
    backgroundColor: "#fee2e2", color: "#dc2626", padding: "12px",
    borderRadius: "8px", marginBottom: "16px", fontSize: "14px"
  },
  statsGrid: {
    display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
    gap: "16px", marginBottom: "24px"
  },
  statCard: {
    borderRadius: "12px", padding: "18px 20px",
    display: "flex", alignItems: "center", gap: "14px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  statIcon: {
    padding: "10px", borderRadius: "10px",
    backgroundColor: "#ffffff"
  },
  statLabel: { fontSize: "12px", color: "#6b7280", margin: "0 0 3px 0" },
  statValue: { fontSize: "22px", fontWeight: "700", color: "#1e293b", margin: 0 },
  revenueBanner: {
    backgroundColor: "#0f2247", borderRadius: "12px",
    padding: "20px 28px", marginBottom: "24px",
    display: "flex", gap: "32px", alignItems: "center"
  },
  revenueLabel: { fontSize: "11px", color: "#93c5fd", margin: "0 0 4px 0", textTransform: "uppercase" },
  revenueValue: { fontSize: "22px", fontWeight: "700", color: "#ffffff", margin: 0 },
  revenueDivider: { width: "1px", height: "40px", backgroundColor: "#1e3a5f" },
  tableCard: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  tableTitle: { fontSize: "16px", fontWeight: "600", color: "#1e293b", marginBottom: "16px" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: {
    textAlign: "left", padding: "10px 12px", fontSize: "11px",
    fontWeight: "700", color: "#6b7280", borderBottom: "1px solid #e5e7eb",
    textTransform: "uppercase", whiteSpace: "nowrap"
  },
  tr: { borderBottom: "1px solid #f3f4f6" },
  td: { padding: "12px", fontSize: "13px", color: "#374151", verticalAlign: "middle" },
  slugCode: {
    backgroundColor: "#f1f5f9", padding: "2px 8px",
    borderRadius: "4px", fontSize: "12px", color: "#475569"
  },
  planSelect: {
    padding: "4px 8px", borderRadius: "6px",
    border: "1px solid #d1d5db", fontSize: "12px",
    cursor: "pointer", outline: "none"
  },
  statusBadge: {
    padding: "3px 10px", borderRadius: "20px",
    fontSize: "11px", fontWeight: "600"
  },
  toggleBtn: {
    border: "none", padding: "5px 10px",
    borderRadius: "6px", cursor: "pointer",
    fontSize: "11px", fontWeight: "600"
  },
};