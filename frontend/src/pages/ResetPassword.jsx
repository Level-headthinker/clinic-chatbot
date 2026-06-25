import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, CheckCircle2, Stethoscope } from "lucide-react";
import api from "../api/axios";
import { useToast } from "../context/ToastContext";

export default function ResetPassword() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const navigate = useNavigate();
  const { notify } = useToast();

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("token");
    if (t) setToken(t);
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) { notify("Passwords do not match.", "error"); return; }
    if (!token) { notify("Missing reset token. Use the link from your email.", "error"); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
    } catch (err) {
      notify(err.response?.data?.detail || "Could not reset password.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-mark"><Stethoscope size={20} color="#fff" /></div>
          <div>
            <h1 style={{ fontSize: 20, marginBottom: 1 }}>ClinicBot</h1>
            <p style={{ fontSize: 12, margin: 0 }}>Set a new password</p>
          </div>
        </div>

        {done ? (
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--success-soft, rgba(22,163,74,.1))", display: "grid", placeItems: "center", margin: "0 auto 16px", color: "#16a34a" }}>
              <CheckCircle2 size={28} />
            </div>
            <h1 style={{ fontSize: 22, marginBottom: 8 }}>Password updated</h1>
            <p style={{ marginBottom: 24 }}>You can now log in with your new password.</p>
            <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", minHeight: 42 }} onClick={() => navigate("/login")}>
              Go to login
            </button>
          </div>
        ) : (
          <>
            <h1 style={{ fontSize: 22, marginBottom: 6 }}>Choose a new password</h1>
            <p style={{ marginBottom: 24 }}>At least 8 characters, with a letter and a number.</p>
            <form onSubmit={submit} className="form-stack">
              <div className="field">
                <label>New password</label>
                <input className="input" type="password" value={password} required autoFocus
                  onChange={(e) => setPassword(e.target.value)} placeholder="New password" />
              </div>
              <div className="field">
                <label>Confirm password</label>
                <input className="input" type="password" value={confirm} required
                  onChange={(e) => setConfirm(e.target.value)} placeholder="Repeat new password" />
              </div>
              <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center", minHeight: 42 }}>
                <Lock size={16} /> {loading ? "Updating…" : "Reset password"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
