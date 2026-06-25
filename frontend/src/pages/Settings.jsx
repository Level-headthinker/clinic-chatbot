import { useCallback, useEffect, useState } from "react";
import { Save, Bot, Building2, Palette, MessageCircle, Code } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useToast } from "../context/ToastContext";

const TIMEZONES = ["Asia/Karachi", "Asia/Kolkata", "Asia/Dubai", "UTC"];

const TONES = [
  { value: "warm", label: "Warm & friendly", desc: "Caring, like a kind receptionist", sample: "Bilkul! Main aap ki madad ke liye hoon. 😊" },
  { value: "formal", label: "Formal & polished", desc: "Respectful and proper", sample: "Certainly. I would be pleased to assist you." },
  { value: "casual", label: "Casual & relaxed", desc: "Friendly and conversational", sample: "Sure thing! What do you need help with?" },
  { value: "professional", label: "Professional & efficient", desc: "Clear and to the point", sample: "Of course. Which doctor would you like to see?" },
  { value: "concise", label: "Concise & direct", desc: "Fewest words needed", sample: "Sure — which day works for you?" },
];

const defaultForm = {
  clinic_name: "",
  bot_name: "",
  welcome_message: "",
  bot_tone: "warm",
  primary_color: "#0d9488",
  branch_bot_name: "",
  branch_welcome_message: "",
  branch_address: "",
  branch_city: "",
  branch_phone: "",
  branch_timezone: "Asia/Karachi",
  branch_working_hours: "",
};

export default function Settings() {
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/settings");
      setForm((prev) => ({ ...prev, ...res.data }));
    } catch {
      notify("Failed to load settings.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { load(); }, [load]);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put("/settings", form);
      notify("Settings saved.", "success");
    } catch {
      notify("Failed to save settings.", "error");
    } finally {
      setSaving(false);
    }
  };

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  if (loading) return <AppLayout title="Settings"><div className="empty-state"><p>Loading…</p></div></AppLayout>;

  return (
    <AppLayout title="Settings" subtitle="Configure your clinic's AI bot, branding, and branch details.">
      <form onSubmit={save} style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* Clinic & Bot */}
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Bot size={18} style={{ color: "var(--primary)" }} />
              <h3>Clinic & AI Bot</h3>
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Clinic Name</label>
              <input className="input" value={form.clinic_name} onChange={set("clinic_name")}
                placeholder="City Clinic" />
            </div>
            <div className="field">
              <label>Bot Name</label>
              <input className="input" value={form.bot_name} onChange={set("bot_name")}
                placeholder="City Clinic Assistant" />
              <p className="field-hint">This is how the AI introduces itself to patients.</p>
            </div>
          </div>
          <div className="field">
            <label>Welcome Message</label>
            <textarea className="input" rows={3} value={form.welcome_message}
              onChange={set("welcome_message")}
              placeholder="Hello! I'm your clinic assistant. How can I help you today?" />
            <p className="field-hint">First message patients see when they open the chat widget.</p>
          </div>
          <div className="field">
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <MessageCircle size={15} /> Conversation Tone
            </label>
            <p className="field-hint" style={{ marginTop: 0, marginBottom: 10 }}>
              How the bot sounds to patients. It only shapes the style — the safety rules never change.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
              {TONES.map((t) => {
                const active = (form.bot_tone || "warm") === t.value;
                return (
                  <button
                    type="button"
                    key={t.value}
                    onClick={() => setForm((f) => ({ ...f, bot_tone: t.value }))}
                    style={{
                      textAlign: "left", padding: "12px 14px", borderRadius: 10, cursor: "pointer",
                      border: `2px solid ${active ? "var(--primary)" : "var(--line)"}`,
                      background: active ? "var(--primary-soft, rgba(13,148,136,.08))" : "var(--surface)",
                      transition: "all .15s",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <strong style={{ fontSize: 14, color: active ? "var(--primary-text, var(--primary))" : "var(--text-1)" }}>{t.label}</strong>
                      <span style={{
                        width: 16, height: 16, borderRadius: "50%", flexShrink: 0,
                        border: `2px solid ${active ? "var(--primary)" : "var(--line)"}`,
                        background: active ? "var(--primary)" : "transparent",
                        display: "grid", placeItems: "center",
                      }}>{active && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff" }} />}</span>
                    </div>
                    <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--muted)" }}>{t.desc}</p>
                    <p style={{ margin: "8px 0 0", fontSize: 12, fontStyle: "italic", color: "var(--text-2, var(--muted))" }}>“{t.sample}”</p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Branding */}
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Palette size={18} style={{ color: "var(--primary)" }} />
              <h3>Branding</h3>
            </div>
          </div>
          <div className="field" style={{ maxWidth: 200 }}>
            <label>Primary Color</label>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <input type="color" value={form.primary_color} onChange={set("primary_color")}
                style={{ width: 44, height: 36, border: "1px solid var(--line)", borderRadius: "var(--radius)", cursor: "pointer", padding: 2 }} />
              <input className="input" value={form.primary_color} onChange={set("primary_color")}
                placeholder="#0d9488" style={{ flex: 1 }} maxLength={7} />
            </div>
            <p className="field-hint">Used for the chat widget button and accents.</p>
          </div>
        </div>

        {/* Branch Details */}
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Building2 size={18} style={{ color: "var(--primary)" }} />
              <h3>Branch Details</h3>
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Branch Bot Name <span style={{ color: "var(--muted)", fontWeight: 400 }}>(overrides clinic bot name)</span></label>
              <input className="input" value={form.branch_bot_name || ""} onChange={set("branch_bot_name")}
                placeholder="Leave blank to use clinic bot name" />
            </div>
            <div className="field">
              <label>Branch Phone</label>
              <input className="input" value={form.branch_phone || ""} onChange={set("branch_phone")}
                placeholder="+92 300 1234567" />
            </div>
            <div className="field">
              <label>City</label>
              <input className="input" value={form.branch_city || ""} onChange={set("branch_city")}
                placeholder="Lahore" />
            </div>
            <div className="field">
              <label>Timezone</label>
              <select className="input" value={form.branch_timezone} onChange={set("branch_timezone")}>
                {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label>Address</label>
            <input className="input" value={form.branch_address || ""} onChange={set("branch_address")}
              placeholder="123 Main Street, Model Town" />
          </div>
          <div className="field">
            <label>Working Hours</label>
            <input className="input" value={form.branch_working_hours || ""} onChange={set("branch_working_hours")}
              placeholder="Mon–Sat 9am–9pm, Sunday closed" />
            <p className="field-hint">The bot uses this to answer patient questions about clinic hours.</p>
          </div>
          <div className="field">
            <label>Branch Welcome Message <span style={{ color: "var(--muted)", fontWeight: 400 }}>(overrides clinic message)</span></label>
            <textarea className="input" rows={2} value={form.branch_welcome_message || ""}
              onChange={set("branch_welcome_message")}
              placeholder="Leave blank to use clinic welcome message" />
          </div>
        </div>

        {/* Embed snippet */}
        {form.branch_slug && (
          <div className="panel">
            <div className="panel-header" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Code size={18} style={{ color: "var(--primary)" }} />
                <h3>Chat Widget Embed Code</h3>
              </div>
            </div>
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
              Paste this snippet before the <code>&lt;/body&gt;</code> tag on your clinic website.
            </p>
            <pre style={{
              background: "var(--surface-2)", border: "1px solid var(--line)",
              borderRadius: "var(--radius)", padding: "12px 16px", fontSize: 12,
              overflowX: "auto", fontFamily: "monospace", color: "var(--text-2)",
            }}>
{`<script>
  window.CLINIC_SLUG = "${form.branch_slug}";
</script>
<script src="${window.location.origin}/widget.js" defer></script>`}
            </pre>
            <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
              Self-booking link:{" "}
              <a href={`/book/${form.branch_slug}`} target="_blank" rel="noreferrer"
                style={{ color: "var(--primary)" }}>
                {window.location.origin}/book/{form.branch_slug}
              </a>
            </p>
          </div>
        )}

        <div className="action-row">
          <button className="btn btn-primary" type="submit" disabled={saving}>
            <Save size={15} />
            {saving ? "Saving…" : "Save Settings"}
          </button>
        </div>
      </form>
    </AppLayout>
  );
}
