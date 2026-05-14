import { useCallback, useEffect, useState } from "react";
import { Calendar, DollarSign, MessageSquare, Stethoscope, Users } from "lucide-react";
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

  return (
    <AppLayout
      title="Super Admin"
      subtitle="Platform-wide clinic, revenue, and usage overview."
    >
      {loading ? (
        <DashboardSkeleton />
      ) : (
        <>
          {stats && (
            <div className="metric-grid">
              <Metric icon={<Users size={22} />} label="Clinics" value={stats.total_clinics} />
              <Metric icon={<Calendar size={22} />} label="Appointments" value={stats.total_appointments} />
              <Metric icon={<Users size={22} />} label="Leads" value={stats.total_leads} />
              <Metric icon={<Stethoscope size={22} />} label="Doctors" value={stats.total_doctors} />
              <Metric icon={<MessageSquare size={22} />} label="Chats" value={stats.total_chats} />
              <Metric icon={<DollarSign size={22} />} label="MRR" value={`PKR ${stats.estimated_mrr.toLocaleString()}`} />
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
                  <tr>{["Clinic", "Slug", "Plan", "Doctors", "Leads", "Appts", "Chats", "Status", "Joined", "Actions"].map((h) => <th key={h}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {clinics.map((clinic) => (
                    <tr key={clinic.id}>
                      <td data-label="Clinic"><strong>{clinic.name}</strong></td>
                      <td data-label="Slug"><code>{clinic.slug}</code></td>
                      <td data-label="Plan">
                        <select className="select" value={clinic.plan} onChange={(e) => updatePlan(clinic.id, e.target.value)}>
                          <option value="starter">Starter</option>
                          <option value="growth">Growth</option>
                          <option value="enterprise">Enterprise</option>
                        </select>
                      </td>
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
                        <button className={clinic.is_active ? "btn btn-danger" : "btn btn-primary"} onClick={() => toggleClinic(clinic.id, clinic.name)}>
                          {clinic.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
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
