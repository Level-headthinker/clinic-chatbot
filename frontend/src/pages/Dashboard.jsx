import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Calendar, Clock, Plus, Stethoscope, TrendingUp, Users } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { DashboardSkeleton } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/dashboard/summary");
      setData(res.data);
    } catch {
      notify("Dashboard data could not be loaded.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const leads = data?.leads ?? {};
  const appts = data?.appointments ?? {};
  const patients = data?.patients ?? {};
  const doctors = data?.doctors ?? {};
  const recent = data?.recent_appointments ?? [];
  const branches = data?.branches ?? [];
  const todayAppts = data?.today_appointments ?? [];
  const dueFollowups = data?.due_followups ?? [];

  return (
    <AppLayout
      title="Dashboard"
      subtitle="A live overview of leads, bookings, and clinic conversion."
      actions={
        <button className="btn btn-primary" onClick={() => navigate("/doctors")}>
          <Plus size={16} />
          Add doctor
        </button>
      }
    >
      {loading ? (
        <DashboardSkeleton />
      ) : (
        <>
          <div className="metric-grid">
            <MetricCard
              icon={<Users size={22} />}
              label="Total leads"
              value={leads.total ?? 0}
              sub={leads.this_month > 0 ? `+${leads.this_month} this month` : null}
              trend={leads.trend}
            />
            <MetricCard
              icon={<Clock size={22} />}
              label="Conversion rate"
              value={leads.conversion_rate ?? "0%"}
              sub={`${leads.converted ?? 0} converted`}
            />
            <MetricCard
              icon={<Calendar size={22} />}
              label="Appointments"
              value={appts.total ?? 0}
              sub={appts.today > 0 ? `${appts.today} today` : `${appts.this_week ?? 0} this week`}
            />
            <MetricCard
              icon={<TrendingUp size={22} />}
              label="Patients"
              value={patients.total ?? 0}
              sub={patients.new_this_month > 0 ? `+${patients.new_this_month} this month` : null}
            />
          </div>

          {appts.pending > 0 || appts.confirmed > 0 ? (
            <div className="metric-grid" style={{ marginTop: 0 }}>
              <StatChip label="Pending" value={appts.pending ?? 0} color="warning" />
              <StatChip label="Confirmed" value={appts.confirmed ?? 0} color="success" />
              <StatChip label="Completed" value={appts.completed ?? 0} color="neutral" />
              <StatChip label="Active doctors" value={doctors.active ?? 0} color="neutral" icon={<Stethoscope size={14} />} />
            </div>
          ) : null}

          {branches.length > 0 && (
            <section className="table-panel">
              <div className="panel-header">
                <h2>Branch breakdown</h2>
              </div>
              <table className="responsive-table">
                <thead>
                  <tr>
                    {["Branch", "Leads", "Appointments", "Pending", "Doctors"].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {branches.map((b) => (
                    <tr key={b.id}>
                      <td data-label="Branch">
                        {b.name}
                        {b.is_main_branch && (
                          <span className="badge badge-success" style={{ marginLeft: 6, fontSize: 11 }}>main</span>
                        )}
                      </td>
                      <td data-label="Leads">{b.leads}</td>
                      <td data-label="Appointments">{b.appointments}</td>
                      <td data-label="Pending">{b.pending_appointments}</td>
                      <td data-label="Doctors">{b.active_doctors}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* Today's appointments */}
          <section className="table-panel">
            <div className="panel-header">
              <h2>Today's appointments</h2>
              <button className="btn btn-secondary" onClick={() => navigate("/appointments")}>View all</button>
            </div>
            {todayAppts.length === 0 ? (
              <p style={{ padding: "16px 20px", color: "var(--muted)", fontSize: 13 }}>No appointments scheduled for today.</p>
            ) : (
              <table className="responsive-table">
                <thead>
                  <tr>{["Patient", "Phone", "Doctor", "Time", "Status"].map((h) => <th key={h}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {todayAppts.map((a) => (
                    <tr key={a.id}>
                      <td data-label="Patient">{a.patient_name}</td>
                      <td data-label="Phone">{a.patient_phone}</td>
                      <td data-label="Doctor">{a.doctor_name}</td>
                      <td data-label="Time">{new Date(a.slot_datetime).toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })}</td>
                      <td data-label="Status"><span className={`badge ${badgeClass(a.status)}`}>{a.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Due follow-ups */}
          {dueFollowups.length > 0 && (
            <section className="table-panel">
              <div className="panel-header">
                <h2>Follow-ups due today</h2>
                <button className="btn btn-secondary" onClick={() => navigate("/follow-ups")}>View all</button>
              </div>
              <table className="responsive-table">
                <thead>
                  <tr>{["Title", "Due", ""].map((h) => <th key={h}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {dueFollowups.map((f) => (
                    <tr key={f.id}>
                      <td data-label="Title">
                        <strong>{f.title}</strong>
                      </td>
                      <td data-label="Due">
                        <span style={{ color: f.overdue ? "var(--danger)" : "var(--text-1)", fontSize: 13 }}>
                          {f.overdue ? "Overdue · " : ""}{new Date(f.due_date).toLocaleString()}
                        </span>
                      </td>
                      <td>
                        {f.overdue && <AlertCircle size={15} style={{ color: "var(--danger)", verticalAlign: "middle" }} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="table-panel">
            <div className="panel-header">
              <h2>Recent appointments</h2>
              <button className="btn btn-secondary" onClick={() => navigate("/appointments")}>
                View all
              </button>
            </div>
            {recent.length === 0 ? (
              <EmptyState
                title="No appointments yet"
                description="Once patients confirm through the chatbot, appointments will appear here."
                action={
                  <button className="btn btn-primary" onClick={() => navigate("/chat-preview")}>
                    Test chatbot
                  </button>
                }
              />
            ) : (
              <table className="responsive-table">
                <thead>
                  <tr>
                    {["Patient", "Phone", "Doctor", "Slot", "Status"].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recent.map((a) => (
                    <tr key={a.id}>
                      <td data-label="Patient">{a.patient_name}</td>
                      <td data-label="Phone">{a.patient_phone}</td>
                      <td data-label="Doctor">{a.doctor_name}</td>
                      <td data-label="Slot">{new Date(a.slot_datetime).toLocaleString()}</td>
                      <td data-label="Status">
                        <span className={`badge ${badgeClass(a.status)}`}>{a.status}</span>
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

function MetricCard({ icon, label, value, sub, trend }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div>
        <p className="metric-label">{label}</p>
        <p className="metric-value">{value}</p>
        {sub && <p className="metric-sub">{sub}</p>}
      </div>
      {trend && trend !== "0%" && (
        <span className={`metric-trend ${trend.startsWith("+") ? "up" : "down"}`}>{trend}</span>
      )}
    </div>
  );
}

function StatChip({ label, value, color, icon }) {
  return (
    <div className={`stat-chip stat-chip--${color}`}>
      {icon && <span className="stat-chip-icon">{icon}</span>}
      <span className="stat-chip-value">{value}</span>
      <span className="stat-chip-label">{label}</span>
    </div>
  );
}

function badgeClass(status) {
  if (status === "confirmed" || status === "completed") return "badge-success";
  if (status === "cancelled" || status === "no_show") return "badge-danger";
  return "badge-warning";
}
