import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";

export default function Register() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    clinic_name: "",
    clinic_slug: "",
    admin_email: "",
    admin_password: "",
    confirm_password: "",
    admin_full_name: "",
    phone: "",
    city: "",
  });

  const updateForm = (field, value) => {
    setForm({ ...form, [field]: value });
    if (field === "clinic_name") {
      const slug = value
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9-]/g, "");
      setForm((prev) => ({ ...prev, clinic_name: value, clinic_slug: slug }));
    }
  };

  const validateStep1 = () => {
    if (!form.clinic_name) return "Clinic name is required";
    if (!form.clinic_slug) return "Clinic slug is required";
    if (form.clinic_slug.length < 3) return "Slug must be at least 3 characters";
    return null;
  };

  const validateStep2 = () => {
    if (!form.admin_full_name) return "Your name is required";
    if (!form.admin_email) return "Email is required";
    if (!form.admin_email.includes("@")) return "Enter a valid email";
    if (!form.admin_password) return "Password is required";
    if (form.admin_password.length < 6) return "Password must be at least 6 characters";
    if (form.admin_password !== form.confirm_password) return "Passwords do not match";
    return null;
  };

  const handleNext = () => {
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
      if (msg === "Clinic slug already taken") {
        setError("This clinic URL is already taken. Try a different name.");
      } else if (msg === "Email already registered") {
        setError("This email is already registered. Please login.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.successIcon}>🎉</div>
          <h2 style={styles.successTitle}>You are all set!</h2>
          <p style={styles.successText}>
            Your clinic has been registered successfully.
            Login to set up your doctors and start capturing patients.
          </p>
          <div style={styles.successInfo}>
            <p style={{ margin: "0 0 6px 0", fontSize: "13px", color: "#64748b" }}>
              Your chat widget URL:
            </p>
            <code style={styles.code}>
              clinicbot.pk/widget/{form.clinic_slug}
            </code>
          </div>
          <button
            onClick={() => navigate("/login")}
            style={styles.button}
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>

        {/* Header */}
        <div style={styles.header}>
          <h1 style={styles.logo}>🏥 ClinicBot</h1>
          <p style={styles.subtitle}>Register your clinic — free for 30 days</p>
        </div>

        {/* Step indicator */}
        <div style={styles.steps}>
          <div style={styles.stepRow}>
            <div style={{
              ...styles.stepCircle,
              backgroundColor: step >= 1 ? "#2563eb" : "#e2e8f0",
              color: step >= 1 ? "#fff" : "#94a3b8"
            }}>1</div>
            <div style={{
              ...styles.stepLine,
              backgroundColor: step >= 2 ? "#2563eb" : "#e2e8f0"
            }} />
            <div style={{
              ...styles.stepCircle,
              backgroundColor: step >= 2 ? "#2563eb" : "#e2e8f0",
              color: step >= 2 ? "#fff" : "#94a3b8"
            }}>2</div>
          </div>
          <div style={styles.stepLabels}>
            <span style={{ fontSize: "11px", color: step === 1 ? "#2563eb" : "#94a3b8" }}>
              Clinic Info
            </span>
            <span style={{ fontSize: "11px", color: step === 2 ? "#2563eb" : "#94a3b8" }}>
              Your Account
            </span>
          </div>
        </div>

        {/* Error */}
        {error && <div style={styles.error}>{error}</div>}

        {/* Step 1 — Clinic Info */}
        {step === 1 && (
          <div style={styles.form}>
            <div style={styles.field}>
              <label style={styles.label}>Clinic Name *</label>
              <input
                style={styles.input}
                placeholder="e.g. City Medical Clinic"
                value={form.clinic_name}
                onChange={(e) => updateForm("clinic_name", e.target.value)}
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Clinic URL *</label>
              <div style={styles.slugRow}>
                <span style={styles.slugPrefix}>clinicbot.pk/</span>
                <input
                  style={{ ...styles.input, borderRadius: "0 8px 8px 0", flex: 1 }}
                  placeholder="city-medical-clinic"
                  value={form.clinic_slug}
                  onChange={(e) => updateForm("clinic_slug",
                    e.target.value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "")
                  )}
                />
              </div>
              <p style={styles.hint}>
                This will be your unique clinic link. Auto-generated from clinic name.
              </p>
            </div>

            <div style={styles.field}>
              <label style={styles.label}>City</label>
              <select
                style={styles.input}
                value={form.city}
                onChange={(e) => updateForm("city", e.target.value)}
              >
                <option value="">Select city</option>
                <option>Lahore</option>
                <option>Karachi</option>
                <option>Islamabad</option>
                <option>Rawalpindi</option>
                <option>Faisalabad</option>
                <option>Multan</option>
                <option>Peshawar</option>
                <option>Quetta</option>
                <option>Other</option>
              </select>
            </div>

            <button onClick={handleNext} style={styles.button}>
              Next →
            </button>

            <p style={styles.loginText}>
              Already registered?{" "}
              <span
                onClick={() => navigate("/login")}
                style={styles.loginLink}
              >
                Login here
              </span>
            </p>
          </div>
        )}

        {/* Step 2 — Account Info */}
        {step === 2 && (
          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.field}>
              <label style={styles.label}>Your Full Name *</label>
              <input
                style={styles.input}
                placeholder="Dr. Ahmed Khan"
                value={form.admin_full_name}
                onChange={(e) => updateForm("admin_full_name", e.target.value)}
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Email Address *</label>
              <input
                type="email"
                style={styles.input}
                placeholder="doctor@yourclinic.com"
                value={form.admin_email}
                onChange={(e) => updateForm("admin_email", e.target.value)}
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Password *</label>
              <input
                type="password"
                style={styles.input}
                placeholder="Minimum 6 characters"
                value={form.admin_password}
                onChange={(e) => updateForm("admin_password", e.target.value)}
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Confirm Password *</label>
              <input
                type="password"
                style={styles.input}
                placeholder="Repeat your password"
                value={form.confirm_password}
                onChange={(e) => updateForm("confirm_password", e.target.value)}
              />
            </div>

            {/* Plan info box */}
            <div style={styles.planBox}>
              <p style={styles.planTitle}>🎁 Free Trial — 30 Days</p>
              <p style={styles.planText}>
                No credit card required. Full access to all features.
                After 30 days — only 3,000 PKR/month.
              </p>
            </div>

            <div style={styles.buttonRow}>
              <button
                type="button"
                onClick={() => { setStep(1); setError(""); }}
                style={styles.backButton}
              >
                ← Back
              </button>
              <button
                type="submit"
                style={loading ? styles.buttonDisabled : styles.button}
                disabled={loading}
              >
                {loading ? "Creating account..." : "Create Account"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    backgroundColor: "#f0f4f8",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "20px",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "16px",
    padding: "40px",
    width: "100%",
    maxWidth: "460px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.1)",
  },
  header: {
    textAlign: "center",
    marginBottom: "28px",
  },
  logo: {
    fontSize: "26px",
    fontWeight: "700",
    color: "#1e40af",
    margin: "0 0 6px 0",
  },
  subtitle: {
    color: "#64748b",
    fontSize: "14px",
    margin: 0,
  },
  steps: {
    marginBottom: "24px",
  },
  stepRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0",
    marginBottom: "6px",
  },
  stepCircle: {
    width: "32px",
    height: "32px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "14px",
    fontWeight: "700",
  },
  stepLine: {
    flex: 1,
    height: "3px",
    maxWidth: "120px",
  },
  stepLabels: {
    display: "flex",
    justifyContent: "space-between",
    paddingLeft: "8px",
    paddingRight: "8px",
  },
  error: {
    backgroundColor: "#fee2e2",
    color: "#dc2626",
    padding: "12px",
    borderRadius: "8px",
    marginBottom: "16px",
    fontSize: "13px",
    textAlign: "center",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#374151",
  },
  input: {
    padding: "11px 14px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  },
  slugRow: {
    display: "flex",
    alignItems: "center",
  },
  slugPrefix: {
    backgroundColor: "#f1f5f9",
    border: "1px solid #d1d5db",
    borderRight: "none",
    padding: "11px 10px",
    fontSize: "13px",
    color: "#64748b",
    borderRadius: "8px 0 0 8px",
    whiteSpace: "nowrap",
  },
  hint: {
    fontSize: "11px",
    color: "#94a3b8",
    margin: 0,
  },
  planBox: {
    backgroundColor: "#eff6ff",
    border: "1px solid #bfdbfe",
    borderRadius: "10px",
    padding: "14px 16px",
  },
  planTitle: {
    fontSize: "14px",
    fontWeight: "700",
    color: "#1e40af",
    margin: "0 0 4px 0",
  },
  planText: {
    fontSize: "12px",
    color: "#3b82f6",
    margin: 0,
    lineHeight: "1.5",
  },
  buttonRow: {
    display: "flex",
    gap: "12px",
  },
  button: {
    backgroundColor: "#2563eb",
    color: "#ffffff",
    padding: "12px",
    borderRadius: "8px",
    border: "none",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "pointer",
    flex: 1,
  },
  buttonDisabled: {
    backgroundColor: "#93c5fd",
    color: "#ffffff",
    padding: "12px",
    borderRadius: "8px",
    border: "none",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "not-allowed",
    flex: 1,
  },
  backButton: {
    backgroundColor: "#f1f5f9",
    color: "#374151",
    padding: "12px",
    borderRadius: "8px",
    border: "none",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "pointer",
    width: "100px",
  },
  loginText: {
    textAlign: "center",
    fontSize: "13px",
    color: "#64748b",
    margin: 0,
  },
  loginLink: {
    color: "#2563eb",
    fontWeight: "600",
    cursor: "pointer",
  },
  successIcon: {
    fontSize: "52px",
    textAlign: "center",
    marginBottom: "16px",
  },
  successTitle: {
    fontSize: "22px",
    fontWeight: "700",
    color: "#1e293b",
    textAlign: "center",
    margin: "0 0 10px 0",
  },
  successText: {
    fontSize: "14px",
    color: "#64748b",
    textAlign: "center",
    lineHeight: "1.6",
    margin: "0 0 20px 0",
  },
  successInfo: {
    backgroundColor: "#f0fdf4",
    border: "1px solid #86efac",
    borderRadius: "8px",
    padding: "14px",
    marginBottom: "20px",
  },
  code: {
    display: "block",
    backgroundColor: "#dcfce7",
    padding: "8px 12px",
    borderRadius: "6px",
    fontSize: "13px",
    color: "#16a34a",
    wordBreak: "break-all",
  },
};