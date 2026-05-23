import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Stethoscope } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await login(email, password);
      // Navigate based on the role the backend actually returned — never guess
      navigate(data.role === "doctor" ? "/doctor" : "/dashboard", { replace: true });
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        (err.response?.status === 429
          ? "Too many attempts. Please wait a few minutes."
          : err.response?.status === 403
          ? "Your clinic account has been disabled. Contact support."
          : "Invalid email or password.");
      notify(msg, "error");
    } finally {
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
            <label>Password</label>
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
