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

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch {
      notify("Invalid email or password.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 24 }}>
          <div className="brand-mark">
            <Stethoscope size={22} />
          </div>
          <div>
            <h1 style={{ fontSize: 28 }}>ClinicBot</h1>
            <p style={{ margin: 0 }}>Admin dashboard login</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
          <label>
            <span className="metric-label">Email</span>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@yourclinic.com"
              required
              style={{ width: "100%", marginTop: 6 }}
            />
          </label>

          <label>
            <span className="metric-label">Password</span>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 6 characters"
              required
              style={{ width: "100%", marginTop: 6 }}
            />
          </label>

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
            <ArrowRight size={16} />
          </button>
        </form>

        <p style={{ textAlign: "center", marginBottom: 0 }}>
          New clinic?{" "}
          <button className="btn btn-secondary" onClick={() => navigate("/register")}>
            Register free
          </button>
        </p>
      </div>
    </div>
  );
}
