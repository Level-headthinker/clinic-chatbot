import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Doctors from "./pages/Doctors";
import Appointments from "./pages/Appointments";
import Leads from "./pages/Leads";
import ChatPreview from "./pages/ChatPreview";
import SuperAdmin from "./pages/SuperAdmin";
import Patients from "./pages/Patients";
import PatientDetail from "./pages/PatientDetail";
import Billing from "./pages/Billing";
import Branches from "./pages/Branches";
import Users from "./pages/Users";
import FollowUps from "./pages/FollowUps";
import Voice from "./pages/Voice";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import BookingPage from "./pages/BookingPage";
import WaitingRoom from "./pages/WaitingRoom";
import Services from "./pages/Services";
import Reports from "./pages/Reports";
import DataImport from "./pages/DataImport";
import Conversations from "./pages/Conversations";
import KnowledgeBase from "./pages/KnowledgeBase";
import Subscription from "./pages/Subscription";
import DoctorPortal from "./pages/DoctorPortal";
import Landing from "./pages/Landing";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastProvider } from "./context/ToastContext";
import { SkeletonBlock } from "./components/Skeleton";
import { usePlan } from "./hooks/usePlan";
import { UPGRADE_MESSAGE, PLANS } from "./config/plans";
import { Lock } from "lucide-react";
import AppLayout from "./components/AppLayout";

function ProtectedRoute({ children }) {
  const { user, loading, waking } = useAuth();
  if (loading) {
    return (
      <div className="app-main" style={{ marginLeft: 0 }}>
        <SkeletonBlock className="panel skeleton-table" />
        {waking && (
          <p style={{ textAlign: "center", color: "var(--muted)", marginTop: 16, fontSize: 14 }}>
            Server is starting up, please wait a moment...
          </p>
        )}
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  // Safety net: doctor accidentally on an admin route → send to doctor portal
  if (user.role === "doctor") return <Navigate to="/doctor" replace />;
  return children;
}

function DoctorRoute({ children }) {
  const { user, loading, waking } = useAuth();
  if (loading) {
    return (
      <div className="app-main" style={{ marginLeft: 0 }}>
        <SkeletonBlock className="panel skeleton-table" />
        {waking && (
          <p style={{ textAlign: "center", color: "var(--muted)", marginTop: 16, fontSize: 14 }}>
            Server is starting up, please wait a moment...
          </p>
        )}
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "doctor") return <Navigate to="/dashboard" replace />;
  return children;
}

function PlanRoute({ children, feature }) {
  const { user, loading } = useAuth();
  const { can, plan } = usePlan();

  if (loading) return <div className="app-main" style={{ marginLeft: 0 }}><SkeletonBlock className="panel skeleton-table" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "doctor") return <Navigate to="/doctor" replace />;

  if (!can(feature)) {
    const info = UPGRADE_MESSAGE[feature];
    const targetPlan = PLANS[info?.need?.toLowerCase()];
    return (
      <AppLayout title={info?.need ? `${info.need} Plan Required` : "Upgrade Required"} subtitle="">
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 20px", textAlign: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", background: "var(--accent-soft)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20 }}>
            <Lock size={28} color="var(--accent)" />
          </div>
          <h2 style={{ margin: "0 0 8px" }}>Upgrade to {info?.need}</h2>
          <p style={{ color: "var(--muted)", maxWidth: 380, marginBottom: 24 }}>{info?.reason}</p>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 28 }}>
            <span className="badge" style={{ background: PLANS[plan]?.color, color: "#fff" }}>{PLANS[plan]?.label}</span>
            <span style={{ color: "var(--muted)" }}>→</span>
            <span className="badge" style={{ background: targetPlan?.color, color: "#fff" }}>{targetPlan?.label}</span>
          </div>
          <a
            href="https://wa.me/923000000000?text=I want to upgrade my clinic plan"
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: "none" }}
          >
            Contact us to upgrade
          </a>
        </div>
      </AppLayout>
    );
  }
  return children;
}

function SuperAdminRoute({ children }) {
  const { user, loading, waking } = useAuth();
  if (loading) {
    return (
      <div className="app-main" style={{ marginLeft: 0 }}>
        <SkeletonBlock className="panel skeleton-table" />
        {waking && (
          <p style={{ textAlign: "center", color: "var(--muted)", marginTop: 16, fontSize: 14 }}>
            Server is starting up, please wait a moment...
          </p>
        )}
      </div>
    );
  }
  if (!user) return <Navigate to="/login" />;
  if (!user.is_superadmin) return <Navigate to="/dashboard" />;
  return children;
}

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/register" element={<Register />} />
              <Route path="/login" element={<Login />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/doctors" element={<ProtectedRoute><Doctors /></ProtectedRoute>} />
              <Route path="/appointments" element={<ProtectedRoute><Appointments /></ProtectedRoute>} />
              <Route path="/leads" element={<ProtectedRoute><Leads /></ProtectedRoute>} />
              <Route path="/chat-preview" element={<ProtectedRoute><ChatPreview /></ProtectedRoute>} />
              <Route path="/conversations" element={<ProtectedRoute><Conversations /></ProtectedRoute>} />
              <Route path="/knowledge" element={<ProtectedRoute><KnowledgeBase /></ProtectedRoute>} />
              <Route path="/patients" element={<ProtectedRoute><Patients /></ProtectedRoute>} />
              <Route path="/patients/:id" element={<ProtectedRoute><PatientDetail /></ProtectedRoute>} />
              <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
              <Route path="/branches" element={<PlanRoute feature="multi_branch"><Branches /></PlanRoute>} />
              <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
              <Route path="/follow-ups" element={<ProtectedRoute><FollowUps /></ProtectedRoute>} />
              <Route path="/voice" element={<PlanRoute feature="voice_agent"><Voice /></PlanRoute>} />
              <Route path="/analytics" element={<PlanRoute feature="analytics"><Analytics /></PlanRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              <Route path="/subscription" element={<ProtectedRoute><Subscription /></ProtectedRoute>} />
              <Route path="/waiting-room" element={<ProtectedRoute><WaitingRoom /></ProtectedRoute>} />
              <Route path="/services" element={<ProtectedRoute><Services /></ProtectedRoute>} />
              <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
              <Route path="/import" element={<ProtectedRoute><DataImport /></ProtectedRoute>} />
              <Route path="/book/:slug" element={<BookingPage />} />
              <Route path="/doctor" element={<DoctorRoute><DoctorPortal /></DoctorRoute>} />
              <Route path="/super" element={<SuperAdminRoute><SuperAdmin /></SuperAdminRoute>} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
