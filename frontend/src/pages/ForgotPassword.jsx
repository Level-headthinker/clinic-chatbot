import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Mail, CheckCircle2, Stethoscope } from "lucide-react";
import api from "../api/axios";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim() });
    } catch {
      /* still show the same confirmation — never reveal if the email exists */
    } finally {
      setLoading(false);
      setSent(true);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-mark"><Stethoscope size={20} color="#fff" /></div>
          <div>
            <h1 style={{ fontSize: 20, marginBottom: 1 }}>ClinicBot</h1>
            <p style={{ fontSize: 12, margin: 0 }}>Password reset</p>
          </div>
        </div>

        {sent ? (
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--success-soft, rgba(22,163,74,.1))", display: "grid", placeItems: "center", margin: "0 auto 16px", color: "#16a34a" }}>
              <CheckCircle2 size={28} />
            </div>
            <h1 style={{ fontSize: 22, marginBottom: 8 }}>Check your email</h1>
            <p style={{ marginBottom: 24 }}>
              If <strong>{email}</strong> is registered, we've sent a reset link. It expires in 30 minutes.
            </p>
            <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", minHeight: 42 }} onClick={() => navigate("/login")}>
              Back to login
            </button>
          </div>
        ) : (
          <>
            <h1 style={{ fontSize: 22, marginBottom: 6 }}>Forgot your password?</h1>
            <p style={{ marginBottom: 24 }}>Enter your email and we'll send you a reset link.</p>
            <form onSubmit={submit} className="form-stack">
              <div className="field">
                <label>Email address</label>
                <input className="input" type="email" value={email} required autoFocus
                  onChange={(e) => setEmail(e.target.value)} placeholder="admin@yourclinic.com" />
              </div>
              <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center", minHeight: 42 }}>
                <Mail size={16} /> {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <p style={{ textAlign: "center", marginTop: 20, fontSize: 13 }}>
              <button className="btn btn-secondary" style={{ fontSize: 13, padding: "4px 10px", minHeight: "auto" }} onClick={() => navigate("/login")}>
                <ArrowLeft size={14} /> Back to login
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
