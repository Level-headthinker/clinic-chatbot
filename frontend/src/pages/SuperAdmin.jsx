import { Fragment, useCallback, useEffect, useState } from "react";
import { Bot, BookOpen, Building2, Calendar, ChevronDown, ChevronRight, DollarSign, MessageSquare, Phone, Plus, ShieldAlert, Stethoscope, Target, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { DashboardSkeleton } from "../components/Skeleton";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function SuperAdmin() {
  const [stats, setStats] = useState(null);
  const [clinics, setClinics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedClinic, setExpandedClinic] = useState(null);
  const [branches, setBranches] = useState({});   // { [clinicId]: branch[] | "loading" }
  const { user } = useAuth();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [numbers, setNumbers] = useState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, clinicsRes, numbersRes] = await Promise.all([
        api.get("/super/stats"),
        api.get("/super/clinics"),
        api.get("/super/whatsapp/numbers"),
      ]);
      setStats(statsRes.data);
      setClinics(clinicsRes.data);
      setNumbers(numbersRes.data);
    } catch {
      notify("Failed to load platform data.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  const reloadNumbers = useCallback(async () => {
    try {
      const res = await api.get("/super/whatsapp/numbers");
      setNumbers(res.data);
    } catch {
      notify("Failed to reload WhatsApp numbers.", "error");
    }
  }, [notify]);

  const toggleNumber = async (id) => {
    try {
      await api.put(`/super/whatsapp/numbers/${id}/toggle`);
      reloadNumbers();
    } catch {
      notify("Failed to toggle number.", "error");
    }
  };

  useEffect(() => {
    if (!user?.is_superadmin) {
      navigate("/dashboard");
      return;
    }
    fetchData();
  }, [user, navigate, fetchData]);

  const toggleClinic = async (id, name) => {
    if (!window.confirm(`Toggle status for ${name}?`)) return;
    try {
      await api.put(`/super/clinics/${id}/toggle`);
      notify("Clinic status updated.", "success");
      fetchData();
    } catch {
      notify("Failed to update clinic.", "error");
    }
  };

  const updatePlan = async (id, plan) => {
    try {
      await api.put(`/super/clinics/${id}/plan?plan=${plan}`);
      notify("Clinic plan updated.", "success");
      fetchData();
    } catch {
      notify("Failed to update plan.", "error");
    }
  };

  const toggleBranchExpand = async (clinicId) => {
    if (expandedClinic === clinicId) {
      setExpandedClinic(null);
      return;
    }
    setExpandedClinic(clinicId);
    if (branches[clinicId] && branches[clinicId] !== "loading") return;

    setBranches((prev) => ({ ...prev, [clinicId]: "loading" }));
    try {
      const res = await api.get(`/super/clinics/${clinicId}/branches`);
      setBranches((prev) => ({ ...prev, [clinicId]: res.data }));
    } catch {
      notify("Failed to load branches.", "error");
      setBranches((prev) => ({ ...prev, [clinicId]: [] }));
    }
  };

  const toggleBranch = async (clinicId, branchId, branchName) => {
    if (!window.confirm(`Toggle status for branch "${branchName}"?`)) return;
    try {
      await api.put(`/super/clinics/${clinicId}/branches/${branchId}/toggle`);
      notify("Branch status updated.", "success");
      // Refresh branch list for this clinic
      const res = await api.get(`/super/clinics/${clinicId}/branches`);
      setBranches((prev) => ({ ...prev, [clinicId]: res.data }));
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to update branch.", "error");
    }
  };

  return (
    <AppLayout
      title="Super Admin"
      subtitle="Platform-wide clinic, branch, revenue, and usage overview."
    >
      {loading ? (
        <DashboardSkeleton />
      ) : (
        <>
          {stats && (
            <div className="metric-grid">
              <Metric icon={<Users size={22} />}        label="Clinics"       value={stats.total_clinics} />
              <Metric icon={<Building2 size={22} />}    label="Branches"      value={stats.total_branches ?? 0} />
              <Metric icon={<Calendar size={22} />}     label="Appointments"  value={stats.total_appointments} />
              <Metric icon={<Users size={22} />}        label="Leads"         value={stats.total_leads} />
              <Metric icon={<Stethoscope size={22} />}  label="Doctors"       value={stats.total_doctors} />
              <Metric icon={<MessageSquare size={22} />} label="Chats"        value={stats.total_chats} />
              <Metric icon={<DollarSign size={22} />}   label="Est. MRR"      value={`PKR ${stats.estimated_mrr?.toLocaleString()}`} />
            </div>
          )}

          <AIFeedback notify={notify} />

          <section className="table-panel">
            <div className="panel-header">
              <h2>All clinics</h2>
              <span className="badge">{clinics.length} clinics</span>
            </div>
            {clinics.length === 0 ? (
              <EmptyState title="No clinics yet" description="Registered clinics will appear here." />
            ) : (
              <table className="responsive-table">
                <thead>
                  <tr>
                    {["", "Clinic", "Plan", "Branches", "Doctors", "Leads", "Appts", "Chats", "Status", "Joined", "Actions"].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {clinics.map((clinic) => (
                    <Fragment key={clinic.id}>
                      <tr>
                        <td style={{ width: 36, padding: "0 8px" }}>
                          <button
                            className="icon-btn"
                            title="View branches"
                            onClick={() => toggleBranchExpand(clinic.id)}
                            aria-label="Toggle branches"
                          >
                            {expandedClinic === clinic.id
                              ? <ChevronDown size={15} />
                              : <ChevronRight size={15} />}
                          </button>
                        </td>
                        <td data-label="Clinic">
                          <strong>{clinic.name}</strong>
                          <br />
                          <code style={{ fontSize: 11, color: "var(--muted)" }}>{clinic.slug}</code>
                        </td>
                        <td data-label="Plan">
                          <select className="select" value={clinic.plan} onChange={(e) => updatePlan(clinic.id, e.target.value)}>
                            <option value="starter">Starter</option>
                            <option value="growth">Growth</option>
                            <option value="enterprise">Enterprise</option>
                          </select>
                        </td>
                        <td data-label="Branches">{clinic.branches ?? 0}</td>
                        <td data-label="Doctors">{clinic.doctors}</td>
                        <td data-label="Leads">{clinic.leads}</td>
                        <td data-label="Appts">{clinic.appointments}</td>
                        <td data-label="Chats">{clinic.chats}</td>
                        <td data-label="Status">
                          <span className={`badge ${clinic.is_active ? "badge-success" : "badge-danger"}`}>
                            {clinic.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td data-label="Joined">{new Date(clinic.created_at).toLocaleDateString()}</td>
                        <td data-label="Actions">
                          <button
                            className={clinic.is_active ? "btn btn-danger" : "btn btn-primary"}
                            onClick={() => toggleClinic(clinic.id, clinic.name)}
                          >
                            {clinic.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </td>
                      </tr>

                      {expandedClinic === clinic.id && (
                        <tr key={`${clinic.id}-branches`}>
                          <td colSpan={11} style={{ padding: 0, background: "var(--bg)" }}>
                            <BranchPanel
                              branches={branches[clinic.id]}
                              clinicId={clinic.id}
                              onToggle={toggleBranch}
                            />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <WhatsAppNumbers
            clinics={clinics}
            numbers={numbers}
            onConnected={reloadNumbers}
            onToggle={toggleNumber}
            notify={notify}
          />
        </>
      )}
    </AppLayout>
  );
}

function WhatsAppNumbers({ clinics, numbers, onConnected, onToggle, notify }) {
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({
    tenant_id: "", phone_number_id: "", whatsapp_number: "",
    waba_id: "", register_pin: "", message_limit_monthly: 1000,
  });
  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  const clinicName = (id) => clinics.find((c) => c.id === id)?.name || "Unknown";

  const connect = async () => {
    if (!form.tenant_id) { notify("Pick a clinic.", "error"); return; }
    if (!form.phone_number_id.trim()) { notify("Enter the Meta phone_number_id.", "error"); return; }
    setBusy(true);
    setResult(null);
    try {
      const res = await api.post("/super/whatsapp/connect", {
        ...form,
        message_limit_monthly: Number(form.message_limit_monthly) || 1000,
        waba_id: form.waba_id.trim() || null,
        register_pin: form.register_pin.trim() || null,
      });
      setResult(res.data);
      notify("Number connected — send it a WhatsApp to test.", "success");
      onConnected();
      setForm({ tenant_id: "", phone_number_id: "", whatsapp_number: "", waba_id: "", register_pin: "", message_limit_monthly: 1000 });
    } catch (e) {
      notify(e.response?.data?.detail || "Connect failed.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="table-panel" style={{ marginTop: 16 }}>
      <div className="panel-header">
        <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Phone size={18} /> WhatsApp Numbers
        </h2>
        <button className="btn btn-primary" onClick={() => setShow((s) => !s)}>
          <Plus size={16} /> {show ? "Close" : "Connect a number"}
        </button>
      </div>

      {show && (
        <div style={{ padding: 16, borderBottom: "1px solid var(--line)" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            After you add the clinic's number to your Meta WABA (one-time OTP step),
            paste its <code>phone_number_id</code> here to route it to the clinic.
            WABA ID + PIN are optional — fill them to auto-subscribe and auto-register.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12 }}>
            <div className="field">
              <label>Clinic *</label>
              <select className="select" value={form.tenant_id} onChange={(e) => set("tenant_id", e.target.value)}>
                <option value="">Select clinic</option>
                {clinics.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Meta phone_number_id *</label>
              <input className="input" placeholder="1234567890..." value={form.phone_number_id} onChange={(e) => set("phone_number_id", e.target.value)} />
            </div>
            <div className="field">
              <label>WhatsApp number</label>
              <input className="input" placeholder="+923001234567" value={form.whatsapp_number} onChange={(e) => set("whatsapp_number", e.target.value)} />
            </div>
            <div className="field">
              <label>WABA ID (optional)</label>
              <input className="input" placeholder="auto-subscribe webhook" value={form.waba_id} onChange={(e) => set("waba_id", e.target.value)} />
            </div>
            <div className="field">
              <label>Register PIN (optional)</label>
              <input className="input" placeholder="6-digit PIN" value={form.register_pin} onChange={(e) => set("register_pin", e.target.value)} />
            </div>
            <div className="field">
              <label>Monthly message limit</label>
              <input className="input" type="number" value={form.message_limit_monthly} onChange={(e) => set("message_limit_monthly", e.target.value)} />
            </div>
          </div>
          <div className="action-row" style={{ marginTop: 12 }}>
            <button className="btn btn-primary" onClick={connect} disabled={busy}>
              {busy ? "Connecting…" : "Connect"}
            </button>
          </div>

          {result?.steps && (
            <div style={{ marginTop: 12, fontSize: 13 }}>
              {result.steps.map((s) => (
                <div key={s.step} style={{ display: "flex", gap: 8, padding: "3px 0" }}>
                  <span>{s.ok === true ? "✅" : s.ok === false ? "❌" : "⚪"}</span>
                  <strong style={{ minWidth: 130 }}>{s.step}</strong>
                  <span className="muted">{s.detail}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {numbers.length === 0 ? (
        <EmptyState icon={Phone} title="No numbers connected" description="Connect a clinic's WhatsApp number to start routing patient messages." />
      ) : (
        <table className="responsive-table" style={{ fontSize: 13 }}>
          <thead>
            <tr>
              {["Clinic", "Number", "phone_number_id", "Used / Limit", "Status", ""].map((h) => <th key={h}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {numbers.map((n) => (
              <tr key={n.id}>
                <td data-label="Clinic"><strong>{n.clinic_name || clinicName(n.tenant_id)}</strong></td>
                <td data-label="Number">{n.whatsapp_number || "—"}</td>
                <td data-label="phone_number_id"><code style={{ fontSize: 11 }}>{n.phone_number_id}</code></td>
                <td data-label="Used / Limit">{n.used} / {n.limit}</td>
                <td data-label="Status">
                  <span className={`badge ${n.is_active ? "badge-success" : "badge-danger"}`}>
                    {n.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <button
                    className={n.is_active ? "btn btn-danger" : "btn btn-primary"}
                    style={{ fontSize: 12, padding: "4px 10px" }}
                    onClick={() => onToggle(n.id)}
                  >
                    {n.is_active ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function BranchPanel({ branches, clinicId, onToggle }) {
  if (branches === "loading") {
    return <p style={{ padding: "14px 24px", color: "var(--muted)", fontSize: 13 }}>Loading branches…</p>;
  }
  if (!branches || branches.length === 0) {
    return <p style={{ padding: "14px 24px", color: "var(--muted)", fontSize: 13 }}>No branches found.</p>;
  }

  return (
    <div style={{ padding: "12px 24px 16px", borderTop: "1px solid var(--line)" }}>
      <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", letterSpacing: "0.05em" }}>
        Branches
      </p>
      <table className="responsive-table" style={{ fontSize: 13 }}>
        <thead>
          <tr>
            {["Name", "Slug", "City", "Leads", "Appts", "Doctors", "Chats", "Status", ""].map((h) => (
              <th key={h} style={{ padding: "8px 12px" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {branches.map((b) => (
            <tr key={b.id}>
              <td style={{ padding: "8px 12px" }} data-label="Name">
                {b.name}
                {b.is_main_branch && (
                  <span className="badge badge-success" style={{ marginLeft: 6, fontSize: 10 }}>main</span>
                )}
              </td>
              <td style={{ padding: "8px 12px" }} data-label="Slug"><code>{b.slug}</code></td>
              <td style={{ padding: "8px 12px" }} data-label="City">{b.city || "—"}</td>
              <td style={{ padding: "8px 12px" }} data-label="Leads">{b.leads}</td>
              <td style={{ padding: "8px 12px" }} data-label="Appts">{b.appointments}</td>
              <td style={{ padding: "8px 12px" }} data-label="Doctors">{b.active_doctors}</td>
              <td style={{ padding: "8px 12px" }} data-label="Chats">{b.chat_sessions}</td>
              <td style={{ padding: "8px 12px" }} data-label="Status">
                <span className={`badge ${b.is_active ? "badge-success" : "badge-danger"}`}>
                  {b.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td style={{ padding: "8px 12px" }}>
                <button
                  className={b.is_active ? "btn btn-danger" : "btn btn-primary"}
                  style={{ fontSize: 12, padding: "4px 10px" }}
                  onClick={() => onToggle(clinicId, b.id, b.name)}
                >
                  {b.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div>
        <p className="metric-label">{label}</p>
        <p className="metric-value">{value}</p>
      </div>
    </div>
  );
}

const _pct = (r) => `${Math.round((Number(r) || 0) * 100)}%`;

// ── Platform-wide AI feedback loop (superadmin only) ───────────────────────────
// Includes the safety (output-guard) rate that is deliberately hidden from the
// per-clinic admin view — this is where we watch for a misbehaving prompt.
function AIFeedback({ notify }) {
  const [fb, setFb] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.get("/super/feedback", { params: { days } })
      .then((res) => { if (alive) setFb(res.data); })
      .catch(() => { if (alive) notify?.("Failed to load AI feedback.", "error"); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [days, notify]);

  return (
    <section className="table-panel" style={{ marginTop: 16 }}>
      <div className="panel-header">
        <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Bot size={18} /> AI feedback loop
        </h2>
        <div style={{ display: "flex", gap: 6 }}>
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              className={`btn ${days === d ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: 12, padding: "6px 11px" }}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading && !fb ? (
        <p style={{ padding: 16, color: "var(--muted)", fontSize: 13 }}>Loading…</p>
      ) : !fb || fb.total_turns === 0 ? (
        <EmptyState title="No conversations yet"
          description="Once patients chat with any clinic's bot, platform metrics appear here." />
      ) : (
        <>
          <div className="metric-grid" style={{ marginBottom: 4 }}>
            <Metric icon={<MessageSquare size={22} />} label="Conversations" value={fb.total_turns.toLocaleString()} />
            <Metric icon={<Building2 size={22} />}     label="Active clinics" value={fb.active_clinics} />
            <Metric icon={<Target size={22} />}        label="Conversion"     value={_pct(fb.conversion_rate)} />
            <Metric icon={<BookOpen size={22} />}      label="Knowledge gaps" value={_pct(fb.kb_miss_rate)} />
            <Metric icon={<ShieldAlert size={22} />}   label="Safety flags"   value={_pct(fb.output_flag_rate)} />
          </div>

          <table className="responsive-table">
            <thead>
              <tr>
                {["Clinic", "Chats", "Booked", "Conversion", "Knowledge gaps", "Safety flags"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fb.clinics.map((c) => (
                <tr key={c.tenant_id || c.clinic_name}>
                  <td data-label="Clinic"><strong>{c.clinic_name}</strong></td>
                  <td data-label="Chats">{c.turns}</td>
                  <td data-label="Booked">{c.booked}</td>
                  <td data-label="Conversion">{_pct(c.conversion_rate)}</td>
                  <td data-label="Knowledge gaps" style={{ color: c.kb_miss_rate >= 0.5 ? "#f59e0b" : "inherit" }}>
                    {_pct(c.kb_miss_rate)}
                  </td>
                  <td data-label="Safety flags" style={{ color: c.output_flag_rate >= 0.1 ? "#ef4444" : "inherit" }}>
                    {_pct(c.output_flag_rate)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
