import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { usePlan } from "../hooks/usePlan";
import { PLANS } from "../config/plans";
import UpgradeModal from "./UpgradeModal";
import {
  BarChart2,
  Bell,
  BookOpen,
  Building2,
  Calendar,
  CreditCard,
  FileBarChart,
  LayoutDashboard,
  Lock,
  LogOut,
  MessageSquare,
  Moon,
  Phone,
  Receipt,
  Scissors,
  Settings,
  Shield,
  Stethoscope,
  Sun,
  Upload,
  UserCheck,
  Users,
  UserCog,
  Sofa,
} from "lucide-react";

// feature: the PLAN_FEATURES key that gates this item (null = always visible)
const navItems = [
  { label: "Dashboard",    icon: LayoutDashboard, path: "/dashboard",    feature: null },
  { label: "Conversations", icon: MessageSquare,  path: "/conversations", feature: null },
  { label: "Knowledge Base", icon: BookOpen,      path: "/knowledge",    feature: null },
  { label: "Analytics",    icon: BarChart2,        path: "/analytics",    feature: "analytics" },
  { label: "Doctors",      icon: Stethoscope,      path: "/doctors",      feature: null },
  { label: "Patients",     icon: UserCheck,        path: "/patients",     feature: null },
  { label: "Appointments", icon: Calendar,         path: "/appointments", feature: null },
  { label: "Waiting Room", icon: Sofa,             path: "/waiting-room", feature: null },
  { label: "Services",     icon: Scissors,         path: "/services",     feature: null },
  { label: "Billing",      icon: Receipt,          path: "/billing",      feature: null },
  { label: "Reports",      icon: FileBarChart,     path: "/reports",      feature: null },
  { label: "Import Data",  icon: Upload,           path: "/import",       feature: null },
  { label: "Leads",        icon: Users,            path: "/leads",        feature: null },
  { label: "Follow-ups",   icon: Bell,             path: "/follow-ups",   feature: null },
  { label: "Voice Agent",  icon: Phone,            path: "/voice",        feature: "voice_agent" },
  { label: "Branches",     icon: Building2,        path: "/branches",     feature: "multi_branch" },
  { label: "Staff",        icon: UserCog,          path: "/users",        feature: null },
  { label: "Chat Preview", icon: MessageSquare,    path: "/chat-preview", feature: null },
  { label: "Subscription", icon: CreditCard,       path: "/subscription", feature: null },
  { label: "Settings",     icon: Settings,         path: "/settings",     feature: null },
];

export default function Sidebar({ open = false, onClose }) {
  const { user, logout } = useAuth();
  const { can, plan } = usePlan();
  const navigate = useNavigate();
  const location = useLocation();
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem("theme") === "dark"
  );
  const [upgradeFeature, setUpgradeFeature] = useState(null);

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const goTo = (path) => {
    navigate(path);
    onClose?.();
  };

  const handleNavClick = (item) => {
    if (item.feature && !can(item.feature)) {
      setUpgradeFeature(item.feature);
      return;
    }
    goTo(item.path);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-inner">
          <div className="sidebar-brand">
            <div className="brand-mark">
              <Stethoscope size={22} />
            </div>
            <div>
              <p className="brand-title">ClinicBot</p>
              <p className="brand-subtitle">{user?.user_name || "Clinic"}</p>
            </div>
          </div>

          <nav className="sidebar-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const locked = item.feature && !can(item.feature);
              const active = !locked && (
                location.pathname === item.path ||
                (item.path !== "/dashboard" && location.pathname.startsWith(item.path))
              );
              return (
                <button
                  key={item.path}
                  className={`nav-item ${active ? "active" : ""} ${locked ? "nav-item-locked" : ""}`}
                  onClick={() => handleNavClick(item)}
                  title={locked ? `Upgrade to unlock ${item.label}` : item.label}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                  {locked && (
                    <Lock size={13} style={{ marginLeft: "auto", opacity: 0.5 }} />
                  )}
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
            {!user?.is_superadmin && (
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "6px 12px", marginBottom: 4,
                background: "rgba(255,255,255,.04)", borderRadius: 8,
              }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,.45)" }}>Plan</span>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 10,
                  background: PLANS[plan]?.color || "#6b7280", color: "#fff",
                }}>
                  {PLANS[plan]?.label || "Starter"}
                </span>
              </div>
            )}
            <button className="theme-toggle" onClick={() => setDarkMode(!darkMode)}>
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
              <span>{darkMode ? "Light mode" : "Dark mode"}</span>
            </button>
            <button onClick={handleLogout} className="logout-btn">
              <LogOut size={18} />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {upgradeFeature && (
        <UpgradeModal
          feature={upgradeFeature}
          onClose={() => setUpgradeFeature(null)}
        />
      )}
    </>
  );
}
