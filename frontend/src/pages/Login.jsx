import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, Stethoscope } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import api from "../api/axios";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [wakingUp, setWakingUp] = useState(false);
  const { login, user, loading: authLoading } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const wakingTimer = useRef(null);

  // Pre-warm the backend as soon as the login page loads
  useEffect(() => {
    api.get("/health").catch(() => {});
  }, []);

  // Wait for auth check to finish — prevents flash of login form
  if (authLoading) return null;
  // Already logged in → go straight to dashboard
  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    // After 6 seconds show waking message so user knows to wait
    wakingTimer.current = setTimeout(() => setWakingUp(true), 6000);
    try {
      const data = await login(email, password);
      navigate(data.role === "doctor" ? "/doctor" : "/dashboard", { replace: true });
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        (err.response?.status === 429
          ? "Too many attempts. Please wait a few minutes."
          : err.response?.status === 403
          ? "Your clinic account has been disabled. Contact support."
          : err.code === "ECONNABORTED"
          ? "Server took too long to respond. Please try again."
          : "Invalid email or password.");
      notify(msg, "error");
    } finally {
      clearTimeout(wakingTimer.current);
      setWakingUp(false);
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-mark">
            <Stethoscope size={20} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: 20, marginBottom: 1 }}>ClinicBot</h1>
            <p style={{ fontSize: 12, margin: 0 }}>Admin dashboard</p>
          </div>
        </div>

        <h1 style={{ fontSize: 22, marginBottom: 6 }}>Welcome back</h1>
        <p style={{ marginBottom: 24 }}>Sign in to your clinic account.</p>

        <form onSubmit={handleSubmit} className="form-stack">
          <div className="field">
            <label>Email address</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@yourclinic.com"
              required
              autoFocus
            />
          </div>

          <div className="field">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <label>Password</label>
              <button
                type="button"
                onClick={() => navigate("/forgot-password")}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "var(--primary)", padding: 0 }}
              >
                Forgot password?
              </button>
            </div>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              required
            />
          </div>

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center", minHeight: 42 }}>
            {loading ? "Signing in…" : "Sign in"}
            {!loading && <ArrowRight size={16} />}
          </button>

          {wakingUp && (
            <div style={{
              marginTop: 12, padding: "10px 14px", borderRadius: 8,
              background: "rgba(234,179,8,.1)", border: "1px solid rgba(234,179,8,.3)",
              fontSize: 13, color: "#92400e", textAlign: "center", lineHeight: 1.5,
            }}>
              Server is starting up — first load takes ~30 seconds.<br />
              <span style={{ opacity: 0.7 }}>Please wait, do not refresh.</span>
            </div>
          )}
        </form>

        <p style={{ textAlign: "center", marginTop: 20, fontSize: 13 }}>
          No account yet?{" "}
          <button
            className="btn btn-secondary"
            style={{ fontSize: 13, padding: "4px 10px", minHeight: "auto" }}
            onClick={() => navigate("/register")}
          >
            Register free
          </button>
        </p>
      </div>
    </div>
  );
}
