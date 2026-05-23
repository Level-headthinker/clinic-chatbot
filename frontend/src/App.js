import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
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
import DoctorPortal from "./pages/DoctorPortal";
import Landing from "./pages/Landing";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastProvider } from "./context/ToastContext";
import { SkeletonBlock } from "./components/Skeleton";

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
              <Route path="/register" element={<Register />} />
              <Route path="/login" element={<Login />} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/doctors" element={<ProtectedRoute><Doctors /></ProtectedRoute>} />
              <Route path="/appointments" element={<ProtectedRoute><Appointments /></ProtectedRoute>} />
              <Route path="/leads" element={<ProtectedRoute><Leads /></ProtectedRoute>} />
              <Route path="/chat-preview" element={<ProtectedRoute><ChatPreview /></ProtectedRoute>} />
              <Route path="/patients" element={<ProtectedRoute><Patients /></ProtectedRoute>} />
              <Route path="/patients/:id" element={<ProtectedRoute><PatientDetail /></ProtectedRoute>} />
              <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
              <Route path="/branches" element={<ProtectedRoute><Branches /></ProtectedRoute>} />
              <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
              <Route path="/follow-ups" element={<ProtectedRoute><FollowUps /></ProtectedRoute>} />
              <Route path="/voice" element={<ProtectedRoute><Voice /></ProtectedRoute>} />
              <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              <Route path="/waiting-room" element={<ProtectedRoute><WaitingRoom /></ProtectedRoute>} />
              <Route path="/book/:slug" element={<BookingPage />} />
              <Route path="/doctor" element={<DoctorRoute><DoctorPortal /></DoctorRoute>} />
              <Route path="/super" element={<SuperAdminRoute><SuperAdmin /></SuperAdminRoute>} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
