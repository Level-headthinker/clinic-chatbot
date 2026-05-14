import { useCallback, useEffect, useState } from "react";
import { Calendar, Clock, Plus, TrendingUp, Users } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { DashboardSkeleton } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, apptRes] = await Promise.all([
        api.get("/leads/stats"),
        api.get("/appointments/"),
      ]);
      setStats(statsRes.data);
      setAppointments(apptRes.data.slice(0, 8));
    } catch {
      notify("Dashboard data could not be loaded.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
            <MetricCard icon={<Users size={22} />} label="Total leads" value={stats?.total || 0} />
            <MetricCard icon={<Clock size={22} />} label="New leads" value={stats?.new || 0} />
            <MetricCard icon={<Calendar size={22} />} label="Appointments" value={appointments.length} />
            <MetricCard icon={<TrendingUp size={22} />} label="Conversion" value={stats?.conversion_rate || "0%"} />
          </div>

          <section className="table-panel">
            <div className="panel-header">
              <h2>Recent appointments</h2>
              <button className="btn btn-secondary" onClick={() => navigate("/appointments")}>
                View all
              </button>
            </div>
            {appointments.length === 0 ? (
              <EmptyState
                title="No appointments yet"
                description="Once patients confirm through the chatbot, appointments will appear here for staff follow-up."
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
                    {["Patient", "Phone", "Doctor", "Slot", "Status"].map((heading) => (
                      <th key={heading}>{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appointment) => (
                    <tr key={appointment.id}>
                      <td data-label="Patient">{appointment.patient_name}</td>
                      <td data-label="Phone">{appointment.patient_phone}</td>
                      <td data-label="Doctor">{appointment.doctor_name}</td>
                      <td data-label="Slot">
                        {new Date(appointment.slot_datetime).toLocaleString()}
                      </td>
                      <td data-label="Status">
                        <span className={`badge ${badgeClass(appointment.status)}`}>
                          {appointment.status}
                        </span>
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

function MetricCard({ icon, label, value }) {
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

function badgeClass(status) {
  if (status === "confirmed" || status === "completed") return "badge-success";
  if (status === "cancelled" || status === "no_show") return "badge-danger";
  return "badge-warning";
}
