import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  Calendar,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Moon,
  Receipt,
  Shield,
  Stethoscope,
  Sun,
  UserCheck,
  Users,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/dashboard" },
  { label: "Doctors", icon: Stethoscope, path: "/doctors" },
  { label: "Patients", icon: UserCheck, path: "/patients" },
  { label: "Appointments", icon: Calendar, path: "/appointments" },
  { label: "Billing", icon: Receipt, path: "/billing" },
  { label: "Leads", icon: Users, path: "/leads" },
  { label: "Chat Preview", icon: MessageSquare, path: "/chat-preview" },
];

export default function Sidebar({ open = false, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem("theme") === "dark"
  );

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const goTo = (path) => {
    navigate(path);
    onClose?.();
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="sidebar-brand">
        <div className="brand-mark">
          <Stethoscope size={22} />
        </div>
        <div>
          <p className="brand-title">ClinicBot</p>
          <p className="brand-subtitle">{user?.user_name || "Clinic admin"}</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = location.pathname === item.path;
          return (
            <button
              key={item.path}
              className={`nav-item ${active ? "active" : ""}`}
              onClick={() => goTo(item.path)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
        {user?.is_superadmin && (
          <button
            className={`nav-item ${location.pathname === "/super" ? "active" : ""}`}
            onClick={() => goTo("/super")}
          >
            <Shield size={18} />
            <span>Super Admin</span>
          </button>
        )}
      </nav>

      <div className="sidebar-footer">
        <button className="theme-toggle" onClick={() => setDarkMode(!darkMode)}>
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          <span>{darkMode ? "Light mode" : "Dark mode"}</span>
        </button>
        <button onClick={handleLogout} className="logout-btn">
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
