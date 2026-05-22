import { Fragment, useCallback, useEffect, useState } from "react";
import { Building2, Calendar, ChevronDown, ChevronRight, DollarSign, MessageSquare, Stethoscope, Users } from "lucide-react";
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

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, clinicsRes] = await Promise.all([
        api.get("/super/stats"),
        api.get("/super/clinics"),
      ]);
      setStats(statsRes.data);
      setClinics(clinicsRes.data);
    } catch {
      notify("Failed to load platform data.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

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
        </>
      )}
    </AppLayout>
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
