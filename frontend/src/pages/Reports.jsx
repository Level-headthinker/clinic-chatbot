import { useCallback, useEffect, useState } from "react";
import {
  CalendarDays,
  Download,
  FileBarChart,
  Stethoscope,
  Clock,
  Users,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  FileSpreadsheet,
  FileText,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";

const PERIODS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
];

// Superadmin can flip between their platform rollup and a per-clinic drill-down.
const SCOPES = [
  { value: "clinic", label: "My clinic" },
  { value: "platform", label: "Platform (all clinics)" },
  { value: "per_clinic", label: "Per-clinic breakdown" },
];

function periodLabel(report) {
  if (!report) return "";
  const start = new Date(report.period_start);
  const end = new Date(report.period_end);
  end.setDate(end.getDate() - 1); // [start, end) → inclusive end for display
  const fmt = (d) =>
    d.toLocaleDateString("en-PK", { day: "2-digit", month: "short", year: "numeric" });
  return `${fmt(start)} – ${fmt(end)}`;
}

async function downloadFile(reportId, format, notify) {
  try {
    const res = await api.get(`/reports/${reportId}/download?format=${format}`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `report.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch {
    notify(`Could not download the ${format.toUpperCase()} file.`, "error");
  }
}

export default function Reports() {
  const { user } = useAuth();
  const isSuper = !!user?.is_superadmin;

  const [period, setPeriod] = useState("weekly");
  const [refDate, setRefDate] = useState(""); // optional ISO date inside the period
  const [scope, setScope] = useState("clinic");
  const [report, setReport] = useState(null);
  const [perClinic, setPerClinic] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setReport(null);
    setPerClinic([]);
    try {
      const q = `report_type=${period}${refDate ? `&date=${refDate}` : ""}`;
      if (isSuper && scope === "platform") {
        const res = await api.get(`/super-reports/platform?${q}`);
        setReport(res.data);
      } else if (isSuper && scope === "per_clinic") {
        const res = await api.get(`/super-reports/clinics?${q}`);
        setPerClinic(res.data);
      } else {
        const [rep, hist] = await Promise.all([
          api.get(`/reports/clinic?${q}`),
          api.get(`/reports/clinic/history?report_type=${period}&limit=12`),
        ]);
        setReport(rep.data);
        setHistory(hist.data);
      }
    } catch {
      notify("Failed to load reports.", "error");
    } finally {
      setLoading(false);
    }
  }, [period, refDate, scope, isSuper, notify]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const m = report?.metrics || {};

  return (
    <AppLayout
      title="Reports"
      subtitle="Daily, weekly, monthly and yearly performance — exportable as PDF or Excel."
      actions={
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {isSuper && (
            <select className="select" value={scope} onChange={(e) => setScope(e.target.value)}>
              {SCOPES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          )}
          <select className="select" value={period} onChange={(e) => setPeriod(e.target.value)}>
            {PERIODS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <input
            className="input"
            type="date"
            value={refDate}
            onChange={(e) => setRefDate(e.target.value)}
            title="Pick any date inside the period you want (leave blank for the current period)"
            style={{ maxWidth: 170 }}
          />
        </div>
      }
    >
      {loading ? (
        <>
          <div className="metric-grid">
            {[1, 2, 3, 4].map((i) => <SkeletonBlock key={i} className="metric-card skeleton-card" />)}
          </div>
          <SkeletonBlock className="panel skeleton-table" />
        </>
      ) : isSuper && scope === "per_clinic" ? (
        <PerClinicTable rows={perClinic} period={period} notify={notify} />
      ) : !report ? (
        <EmptyState
          icon={FileBarChart}
          title="No report data"
          description="There is no activity recorded for this period yet."
        />
      ) : (
        <>
          {/* Period header + downloads */}
          <section className="table-panel" style={{ marginBottom: 16 }}>
            <div className="panel-header">
              <div>
                <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                  <CalendarDays size={18} /> {periodLabel(report)}
                </h2>
                <p className="muted" style={{ margin: "4px 0 0" }}>
                  {PERIODS.find((p) => p.value === period)?.label} report
                  {isSuper && scope === "platform" ? " · all clinics" : ""}
                </p>
              </div>
              <div className="action-row">
                <button className="btn btn-secondary" onClick={() => downloadFile(report.id, "pdf", notify)}>
                  <FileText size={16} /> PDF
                </button>
                <button className="btn btn-secondary" onClick={() => downloadFile(report.id, "xlsx", notify)}>
                  <FileSpreadsheet size={16} /> Excel
                </button>
              </div>
            </div>
          </section>

          {/* Headline metrics */}
          <div className="metric-grid">
            <Metric icon={<CalendarDays size={22} />} label="Appointments booked" value={m.appointments_booked ?? 0} />
            <Metric icon={<CheckCircle size={22} />} label="Completed" value={m.appointments_completed ?? 0} />
            <Metric icon={<AlertTriangle size={22} />} label="No-shows" value={m.appointments_no_show ?? 0} />
            <Metric icon={<TrendingUp size={22} />} label="Revenue collected" value={`PKR ${(m.revenue?.collected ?? 0).toLocaleString()}`} />
          </div>

          <div className="metric-grid" style={{ marginTop: 4 }}>
            <Metric icon={<Users size={22} />} label="New patients" value={m.new_patients ?? 0} />
            <Metric icon={<Users size={22} />} label="Returning patients" value={m.returning_patients ?? 0} />
            <Metric icon={<Users size={22} />} label="Leads captured" value={m.leads_captured ?? 0} />
            <Metric icon={<TrendingUp size={22} />} label="Messages received" value={m.messages_received ?? 0} />
          </div>

          {/* Highlights */}
          <section className="table-panel" style={{ marginTop: 16 }}>
            <div className="panel-header"><h2>Highlights</h2></div>
            <div className="record-grid" style={{ padding: 12 }}>
              <Info
                icon={<Stethoscope size={16} />}
                label="Busiest doctor"
                value={m.busiest_doctor ? `${m.busiest_doctor.name} (${m.busiest_doctor.appointments})` : "—"}
              />
              <Info
                icon={<Clock size={16} />}
                label="Busiest time slot"
                value={m.busiest_slot ? `${m.busiest_slot.slot} (${m.busiest_slot.appointments})` : "—"}
              />
              <Info label="Revenue billed" value={`PKR ${(m.revenue?.billed ?? 0).toLocaleString()}`} />
              <Info label="Invoices issued" value={m.revenue?.invoices ?? 0} />
              <Info label="Cancelled" value={m.appointments_cancelled ?? 0} />
              <Info label="Chat sessions" value={m.chat_sessions_started ?? 0} />
            </div>
          </section>

          {/* Daily breakdown */}
          {m.daily_appointments && Object.keys(m.daily_appointments).length > 0 && (
            <DailyBreakdown daily={m.daily_appointments} />
          )}

          {/* History (clinic scope only) */}
          {(!isSuper || scope === "clinic") && history.length > 0 && (
            <section className="table-panel" style={{ marginTop: 16 }}>
              <div className="panel-header"><h2>Past {period} reports</h2></div>
              <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                {history.map((h) => (
                  <div key={h.id} className="invoice-top" style={{ alignItems: "center" }}>
                    <div>
                      <strong>{periodLabel(h)}</strong>
                      <p className="muted" style={{ margin: "2px 0 0" }}>
                        {h.metrics?.appointments_booked ?? 0} appts ·{" "}
                        PKR {(h.metrics?.revenue?.collected ?? 0).toLocaleString()} collected
                      </p>
                    </div>
                    <div className="action-row" style={{ justifyContent: "flex-end" }}>
                      <button className="icon-btn" title="Download PDF" onClick={() => downloadFile(h.id, "pdf", notify)}>
                        <Download size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </AppLayout>
  );
}

function PerClinicTable({ rows, period, notify }) {
  if (!rows || rows.length === 0) {
    return <EmptyState icon={FileBarChart} title="No clinics" description="No active clinics for this period." />;
  }
  return (
    <section className="table-panel">
      <div className="panel-header">
        <h2>Per-clinic {period} breakdown</h2>
        <span className="badge">{rows.length} clinics</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="data-table" style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Clinic</th>
              <th>Appts</th>
              <th>Completed</th>
              <th>No-shows</th>
              <th>New</th>
              <th>Returning</th>
              <th>Collected</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const x = r.metrics || {};
              return (
                <tr key={r.id}>
                  <td><strong>{r.clinic_name}</strong></td>
                  <td>{x.appointments_booked ?? 0}</td>
                  <td>{x.appointments_completed ?? 0}</td>
                  <td>{x.appointments_no_show ?? 0}</td>
                  <td>{x.new_patients ?? 0}</td>
                  <td>{x.returning_patients ?? 0}</td>
                  <td>PKR {(x.revenue?.collected ?? 0).toLocaleString()}</td>
                  <td>
                    <button className="icon-btn" title="Download PDF" onClick={() => downloadFile(r.id, "pdf", notify)}>
                      <Download size={15} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DailyBreakdown({ daily }) {
  const entries = Object.entries(daily);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <section className="table-panel" style={{ marginTop: 16 }}>
      <div className="panel-header"><h2>Daily appointments</h2></div>
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
        {entries.map(([date, count]) => (
          <div key={date} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ width: 96, fontSize: 12, color: "var(--muted)" }}>
              {new Date(date).toLocaleDateString("en-PK", { day: "2-digit", month: "short" })}
            </span>
            <div style={{ flex: 1, background: "var(--surface-2)", borderRadius: 6, height: 18, overflow: "hidden" }}>
              <div style={{
                width: `${(count / max) * 100}%`, height: "100%",
                background: "linear-gradient(90deg,#0d9488,#0f766e)", borderRadius: 6,
              }} />
            </div>
            <span style={{ width: 28, textAlign: "right", fontWeight: 700, fontSize: 13 }}>{count}</span>
          </div>
        ))}
      </div>
    </section>
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

function Info({ icon, label, value }) {
  return (
    <div className="record-card">
      <p className="record-label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {icon} {label}
      </p>
      <p className="record-value" style={{ fontSize: 16 }}>{value}</p>
    </div>
  );
}
