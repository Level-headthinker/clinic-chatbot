import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, CheckCircle2, Stethoscope } from "lucide-react";
import api from "../api/axios";

const CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta", "Other"];

const emptyForm = {
  clinic_name: "",
  clinic_slug: "",
  admin_email: "",
  admin_password: "",
  confirm_password: "",
  admin_full_name: "",
  city: "",
};

export default function Register() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const navigate = useNavigate();

  const set = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleClinicName = (value) => {
    const slug = value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
    setForm((prev) => ({ ...prev, clinic_name: value, clinic_slug: slug }));
  };

  const validateStep1 = () => {
    if (!form.clinic_name.trim()) return "Clinic name is required";
    if (!form.clinic_slug || form.clinic_slug.length < 3) return "Clinic URL must be at least 3 characters";
    return null;
  };

  const validateStep2 = () => {
    if (!form.admin_full_name.trim()) return "Your name is required";
    if (!form.admin_email.includes("@")) return "Enter a valid email address";
    if (form.admin_password.length < 8) return "Password must be at least 8 characters";
    if (!/[A-Za-z]/.test(form.admin_password)) return "Password must contain at least one letter";
    if (!/\d/.test(form.admin_password)) return "Password must contain at least one number";
    if (form.admin_password !== form.confirm_password) return "Passwords do not match";
    return null;
  };

  const goNext = () => {
    const err = validateStep1();
    if (err) { setError(err); return; }
    setError("");
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const err = validateStep2();
    if (err) { setError(err); return; }
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/register", {
        clinic_name: form.clinic_name,
        clinic_slug: form.clinic_slug,
        admin_email: form.admin_email,
        admin_password: form.admin_password,
        admin_full_name: form.admin_full_name,
      });
      setSuccess(true);
    } catch (err) {
      const msg = err.response?.data?.detail;
      if (msg === "Clinic slug already taken") setError("This clinic URL is already taken. Try a different name.");
      else if (msg === "Email already registered") setError("This email is already registered. Please log in.");
      else setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--success-soft)", border: "1px solid var(--success-border)", display: "grid", placeItems: "center", margin: "0 auto 16px", color: "var(--success)" }}>
            <CheckCircle2 size={28} />
          </div>
          <h1 style={{ fontSize: 22, marginBottom: 8 }}>You are all set!</h1>
          <p style={{ marginBottom: 20 }}>
            Your clinic has been registered. Log in to configure doctors and start capturing patients.
          </p>
          <div style={{ background: "var(--primary-soft)", border: "1px solid var(--primary-border)", borderRadius: "var(--radius-md)", padding: "14px 16px", marginBottom: 24, textAlign: "left" }}>
            <p style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)", marginBottom: 6 }}>Your chat widget URL</p>
            <code style={{ display: "block", fontSize: 13, color: "var(--primary-text)", wordBreak: "break-all", fontFamily: "monospace" }}>
              clinicbot.pk/widget/{form.clinic_slug}
            </code>
          </div>
          <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", minHeight: 42 }} onClick={() => navigate("/login")}>
            Go to login <ArrowRight size={16} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-mark">
            <Stethoscope size={20} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: 20, marginBottom: 1 }}>ClinicBot</h1>
            <p style={{ fontSize: 12, margin: 0 }}>Free for 30 days</p>
          </div>
        </div>

        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Register your clinic</h1>
        <p style={{ marginBottom: 20 }}>Set up takes under 2 minutes.</p>

        {/* Step indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 24 }}>
          {[1, 2].map((n, i) => (
            <div key={n} style={{ display: "flex", alignItems: "center", flex: i === 0 ? "none" : 1, gap: 0 }}>
              {i > 0 && (
                <div style={{ flex: 1, height: 2, background: step >= n ? "var(--primary)" : "var(--line)", transition: "background 300ms" }} />
              )}
              <div style={{
                width: 28, height: 28, borderRadius: "50%", display: "grid", placeItems: "center",
                fontSize: 13, fontWeight: 700, flexShrink: 0,
                background: step >= n ? "var(--primary)" : "var(--surface-2)",
                color: step >= n ? "#fff" : "var(--muted)",
                border: `2px solid ${step >= n ? "var(--primary)" : "var(--line)"}`,
                transition: "all 200ms",
              }}>{n}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 600, color: "var(--muted)", marginTop: -16, marginBottom: 20 }}>
          <span style={{ color: step === 1 ? "var(--primary)" : "var(--muted)" }}>Clinic info</span>
          <span style={{ color: step === 2 ? "var(--primary)" : "var(--muted)" }}>Your account</span>
        </div>

        {error && (
          <div style={{ background: "var(--danger-soft)", border: "1px solid var(--danger-border)", borderRadius: "var(--radius)", padding: "10px 14px", marginBottom: 16, fontSize: 13, color: "var(--danger)" }}>
            {error}
          </div>
        )}

        {step === 1 && (
          <div className="form-stack">
            <div className="field">
              <label>Clinic name *</label>
              <input className="input" placeholder="City Medical Clinic" value={form.clinic_name} onChange={(e) => handleClinicName(e.target.value)} autoFocus />
            </div>

            <div className="field">
              <label>Clinic URL *</label>
              <div style={{ display: "flex", alignItems: "stretch" }}>
                <span style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRight: "none", padding: "9px 10px", fontSize: 13, color: "var(--muted)", borderRadius: "var(--radius) 0 0 var(--radius)", whiteSpace: "nowrap", display: "flex", alignItems: "center" }}>
                  clinicbot.pk/
                </span>
                <input
                  className="input"
                  style={{ borderRadius: "0 var(--radius) var(--radius) 0", flex: 1 }}
                  placeholder="city-medical-clinic"
                  value={form.clinic_slug}
                  onChange={(e) => set("clinic_slug", e.target.value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, ""))}
                />
              </div>
              <p style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>Auto-generated from clinic name. Can be edited.</p>
            </div>

            <div className="field">
              <label>City</label>
              <select className="select" value={form.city} onChange={(e) => set("city", e.target.value)}>
                <option value="">Select city</option>
                {CITIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>

            <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", minHeight: 42 }} onClick={goNext}>
              Continue <ArrowRight size={16} />
            </button>

            <p style={{ textAlign: "center", fontSize: 13, margin: 0 }}>
              Already registered?{" "}
              <button className="btn btn-secondary" style={{ fontSize: 13, padding: "4px 10px", minHeight: "auto" }} onClick={() => navigate("/login")}>
                Log in
              </button>
            </p>
          </div>
        )}

        {step === 2 && (
          <form onSubmit={handleSubmit} className="form-stack">
            <div className="field">
              <label>Your full name *</label>
              <input className="input" placeholder="Dr. Ahmed Khan" value={form.admin_full_name} onChange={(e) => set("admin_full_name", e.target.value)} autoFocus required />
            </div>
            <div className="field">
              <label>Email address *</label>
              <input className="input" type="email" placeholder="doctor@yourclinic.com" value={form.admin_email} onChange={(e) => set("admin_email", e.target.value)} required />
            </div>
            <div className="field">
              <label>Password *</label>
              <input className="input" type="password" placeholder="Min 8 chars, include a letter and number" value={form.admin_password} onChange={(e) => set("admin_password", e.target.value)} required />
            </div>
            <div className="field">
              <label>Confirm password *</label>
              <input className="input" type="password" placeholder="Repeat your password" value={form.confirm_password} onChange={(e) => set("confirm_password", e.target.value)} required />
            </div>

            <div style={{ background: "var(--primary-soft)", border: "1px solid var(--primary-border)", borderRadius: "var(--radius-md)", padding: "12px 16px" }}>
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--primary-text)", marginBottom: 2 }}>Free trial — 30 days</p>
              <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>No credit card required. Full access to all features.</p>
            </div>

            <div className="action-row">
              <button type="button" className="btn btn-secondary" onClick={() => { setStep(1); setError(""); }}>
                ← Back
              </button>
              <button type="submit" className="btn btn-primary" style={{ flex: 1, justifyContent: "center" }} disabled={loading}>
                {loading ? "Creating account…" : "Create account"}
                {!loading && <ArrowRight size={16} />}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
