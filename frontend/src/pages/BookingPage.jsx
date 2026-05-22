import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Calendar, CheckCircle2, Stethoscope } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

function fmt(slot) {
  return new Date(slot).toLocaleString("en-PK", {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function BookingPage() {
  const { slug } = useParams();
  const [clinic, setClinic] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [step, setStep] = useState(1); // 1=info, 2=doctor+slot, 3=confirm, 4=done
  const [form, setForm] = useState({
    patient_name: "", patient_phone: "", patient_concern: "",
    doctor_id: "", slot_datetime: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/clinic/${slug}`)
      .then((r) => setClinic(r.data))
      .catch(() => setError("Clinic not found. Please check the link."))
      .finally(() => setLoading(false));
  }, [slug]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const selectedDoctor = clinic?.doctors.find((d) => d.id === form.doctor_id);

  const submit = async () => {
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/public/clinic/${slug}/book`, form);
      setResult(res.data);
      setStep(4);
    } catch (err) {
      setError(err.response?.data?.detail || "Booking failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const primaryColor = clinic?.primary_color || "#0d9488";

  if (loading) return (
    <div style={styles.page}>
      <div style={styles.card}><p style={{ color: "#6b7280", textAlign: "center" }}>Loading clinic info…</p></div>
    </div>
  );

  if (error && !clinic) return (
    <div style={styles.page}>
      <div style={styles.card}><p style={{ color: "#ef4444", textAlign: "center" }}>{error}</p></div>
    </div>
  );

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Header */}
        <div style={{ ...styles.header, background: primaryColor }}>
          <div style={styles.logo}><Stethoscope size={26} color="#fff" /></div>
          <h1 style={styles.clinicName}>{clinic.clinic_name}</h1>
          <p style={styles.subtitle}>Book an Appointment</p>
        </div>

        {/* Progress */}
        {step < 4 && (
          <div style={styles.progress}>
            {["Your Info", "Doctor & Slot", "Confirm"].map((label, i) => (
              <div key={i} style={styles.step}>
                <div style={{
                  ...styles.stepDot,
                  background: step > i + 1 ? primaryColor : step === i + 1 ? primaryColor : "#e5e7eb",
                  color: step >= i + 1 ? "#fff" : "#9ca3af",
                }}>{step > i + 1 ? "✓" : i + 1}</div>
                <span style={{ fontSize: 12, color: step === i + 1 ? "#111" : "#9ca3af" }}>{label}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ padding: "24px 28px" }}>
          {error && <p style={styles.errorBox}>{error}</p>}

          {/* Step 1 — Patient info */}
          {step === 1 && (
            <div style={styles.formStack}>
              <h2 style={styles.stepTitle}>Your Details</h2>
              <div style={styles.field}>
                <label style={styles.label}>Full Name *</label>
                <input style={styles.input} value={form.patient_name} onChange={set("patient_name")}
                  placeholder="Ali Khan" />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Phone Number *</label>
                <input style={styles.input} value={form.patient_phone} onChange={set("patient_phone")}
                  placeholder="03001234567" type="tel" />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Reason for Visit</label>
                <textarea style={{ ...styles.input, resize: "vertical" }} rows={3}
                  value={form.patient_concern} onChange={set("patient_concern")}
                  placeholder="e.g. Skin rash, fever, back pain…" />
              </div>
              <button style={{ ...styles.btn, background: primaryColor }}
                disabled={!form.patient_name || !form.patient_phone}
                onClick={() => setStep(2)}>
                Continue →
              </button>
            </div>
          )}

          {/* Step 2 — Doctor & slot */}
          {step === 2 && (
            <div style={styles.formStack}>
              <h2 style={styles.stepTitle}>Choose Doctor & Time</h2>
              <div style={styles.field}>
                <label style={styles.label}>Select Doctor *</label>
                <select style={styles.input} value={form.doctor_id}
                  onChange={(e) => setForm((f) => ({ ...f, doctor_id: e.target.value, slot_datetime: "" }))}>
                  <option value="">— Choose a doctor —</option>
                  {clinic.doctors.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} — {d.specialty} (Rs {d.fee || "N/A"})
                    </option>
                  ))}
                </select>
              </div>
              {selectedDoctor && (
                <div style={styles.field}>
                  <label style={styles.label}>Available Slots *</label>
                  {selectedDoctor.slots.length === 0 ? (
                    <p style={{ color: "#ef4444", fontSize: 13 }}>
                      No available slots in the next 14 days. Please call the clinic.
                    </p>
                  ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                      {selectedDoctor.slots.map((s) => (
                        <button key={s}
                          onClick={() => setForm((f) => ({ ...f, slot_datetime: s }))}
                          style={{
                            padding: "8px 14px", borderRadius: 8, fontSize: 13,
                            border: `2px solid ${form.slot_datetime === s ? primaryColor : "#e5e7eb"}`,
                            background: form.slot_datetime === s ? `${primaryColor}15` : "#fff",
                            color: form.slot_datetime === s ? primaryColor : "#374151",
                            cursor: "pointer", fontWeight: form.slot_datetime === s ? 600 : 400,
                          }}>
                          {fmt(s)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div style={{ display: "flex", gap: 10 }}>
                <button style={{ ...styles.btn, background: "#f3f4f6", color: "#374151" }}
                  onClick={() => setStep(1)}>← Back</button>
                <button style={{ ...styles.btn, background: primaryColor, flex: 1 }}
                  disabled={!form.doctor_id || !form.slot_datetime}
                  onClick={() => setStep(3)}>Review Booking →</button>
              </div>
            </div>
          )}

          {/* Step 3 — Confirm */}
          {step === 3 && (
            <div style={styles.formStack}>
              <h2 style={styles.stepTitle}>Confirm Appointment</h2>
              <div style={styles.summaryCard}>
                <Row label="Name" value={form.patient_name} />
                <Row label="Phone" value={form.patient_phone} />
                {form.patient_concern && <Row label="Concern" value={form.patient_concern} />}
                <Row label="Doctor" value={selectedDoctor?.name} />
                <Row label="Specialty" value={selectedDoctor?.specialty} />
                <Row label="Fee" value={`Rs ${selectedDoctor?.fee || "N/A"}`} />
                <Row label="Date & Time" value={fmt(form.slot_datetime)} />
              </div>
              <p style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
                This creates a <strong>pending</strong> appointment. The clinic will confirm by phone.
              </p>
              <div style={{ display: "flex", gap: 10 }}>
                <button style={{ ...styles.btn, background: "#f3f4f6", color: "#374151" }}
                  onClick={() => setStep(2)}>← Back</button>
                <button style={{ ...styles.btn, background: primaryColor, flex: 1 }}
                  disabled={submitting} onClick={submit}>
                  {submitting ? "Booking…" : "Confirm Appointment"}
                </button>
              </div>
            </div>
          )}

          {/* Step 4 — Done */}
          {step === 4 && result && (
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <CheckCircle2 size={56} color={primaryColor} style={{ marginBottom: 16 }} />
              <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Appointment Requested!</h2>
              <p style={{ color: "#6b7280", marginBottom: 20 }}>
                Your appointment with <strong>{result.doctor}</strong> on{" "}
                <strong>{result.slot}</strong> has been submitted.
              </p>
              <div style={styles.summaryCard}>
                <p style={{ fontSize: 13, color: "#374151" }}>
                  The clinic will call <strong>{form.patient_phone}</strong> to confirm. Please keep your phone reachable.
                </p>
              </div>
              <button style={{ ...styles.btn, background: primaryColor, marginTop: 20 }}
                onClick={() => { setStep(1); setForm({ patient_name: "", patient_phone: "", patient_concern: "", doctor_id: "", slot_datetime: "" }); setResult(null); setError(""); }}>
                Book Another
              </button>
            </div>
          )}
        </div>

        <div style={styles.footer}>Powered by ClinicBot AI</div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f3f4f6" }}>
      <span style={{ fontSize: 13, color: "#6b7280" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: "#111" }}>{value}</span>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#f9fafb", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "32px 16px" },
  card: { background: "#fff", borderRadius: 16, boxShadow: "0 4px 24px rgba(0,0,0,0.08)", width: "100%", maxWidth: 500, overflow: "hidden" },
  header: { padding: "28px 28px 20px", color: "#fff", textAlign: "center" },
  logo: { width: 52, height: 52, borderRadius: "50%", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" },
  clinicName: { fontSize: 22, fontWeight: 700, margin: 0 },
  subtitle: { fontSize: 14, opacity: 0.85, marginTop: 4 },
  progress: { display: "flex", justifyContent: "center", gap: 32, padding: "20px 28px 0", borderBottom: "1px solid #f3f4f6" },
  step: { display: "flex", flexDirection: "column", alignItems: "center", gap: 6 },
  stepDot: { width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700 },
  formStack: { display: "flex", flexDirection: "column", gap: 16 },
  stepTitle: { fontSize: 18, fontWeight: 700, color: "#111", margin: 0 },
  field: { display: "flex", flexDirection: "column", gap: 6 },
  label: { fontSize: 13, fontWeight: 600, color: "#374151" },
  input: { padding: "10px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none", width: "100%", boxSizing: "border-box", fontFamily: "inherit" },
  btn: { padding: "12px 20px", borderRadius: 10, border: "none", cursor: "pointer", fontWeight: 600, fontSize: 14, color: "#fff", opacity: 1, transition: "opacity 0.15s" },
  summaryCard: { background: "#f9fafb", borderRadius: 10, padding: "12px 16px", border: "1px solid #e5e7eb" },
  errorBox: { background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "10px 14px", color: "#dc2626", fontSize: 13 },
  footer: { textAlign: "center", padding: "12px", fontSize: 11, color: "#9ca3af", borderTop: "1px solid #f3f4f6" },
};
