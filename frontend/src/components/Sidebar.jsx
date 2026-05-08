import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard,
  Users,
  Calendar,
  MessageSquare,
  LogOut,
  Stethoscope,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/dashboard" },
  { label: "Doctors", icon: Stethoscope, path: "/doctors" },
  { label: "Appointments", icon: Calendar, path: "/appointments" },
  { label: "Leads", icon: Users, path: "/leads" },
  { label: "Chat Preview", icon: MessageSquare, path: "/chat-preview" },
];
export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div style={styles.sidebar}>
      <div style={styles.logoArea}>
        <h2 style={styles.logo}>🏥 ClinicBot</h2>
        <p style={styles.clinicName}>
          {user?.user_name || "Admin"}
        </p>
      </div>

      <nav style={styles.nav}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              style={isActive ? styles.navItemActive : styles.navItem}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
        {user?.email === "admin@cityclinic.com" && (
          <button
            onClick={() => navigate("/super")}
            style={{
              display: "flex", alignItems: "center", gap: "12px",
              padding: "12px 16px", borderRadius: "8px", border: "none",
              backgroundColor: "#fef9c3", color: "#ca8a04",
              fontSize: "14px", fontWeight: "600", cursor: "pointer",
              textAlign: "left", width: "100%", marginTop: "8px"
            }}
          >
            ⚡ Super Admin
          </button>
        )}
      </nav>

      <button onClick={handleLogout} style={styles.logout}>
        <LogOut size={18} />
        <span>Logout</span>
      </button>
    </div>
  );
}

const styles = {
  sidebar: {
    width: "240px",
    minHeight: "100vh",
    backgroundColor: "#1e3a5f",
    display: "flex",
    flexDirection: "column",
    padding: "24px 16px",
    position: "fixed",
    top: 0,
    left: 0,
  },
  logoArea: {
    marginBottom: "32px",
    paddingBottom: "24px",
    borderBottom: "1px solid #2d5a8e",
  },
  logo: {
    color: "#ffffff",
    fontSize: "20px",
    fontWeight: "700",
    margin: "0 0 4px 0",
  },
  clinicName: {
    color: "#93c5fd",
    fontSize: "12px",
    margin: 0,
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    flex: 1,
  },
  navItem: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 16px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "transparent",
    color: "#93c5fd",
    fontSize: "14px",
    fontWeight: "500",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
  },
  navItemActive: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 16px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#2563eb",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
  },
  logout: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 16px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "transparent",
    color: "#f87171",
    fontSize: "14px",
    fontWeight: "500",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
    marginTop: "auto",
  },
};