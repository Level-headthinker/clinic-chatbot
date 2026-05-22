import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUp, Users, UserCheck, PhoneCall, RefreshCw } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useToast } from "../context/ToastContext";

// ── helpers ────────────────────────────────────────────────────────────────────

function fmt(n) {
  if (n >= 1_000_000) return `Rs ${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `Rs ${(n / 1_000).toFixed(0)}K`;
  return `Rs ${n.toLocaleString()}`;
}

const BRANCH_COLORS = [
  "var(--primary)", "#6366f1", "#f59e0b", "#10b981", "#ef4444",
  "#8b5cf6", "#06b6d4", "#f97316",
];

function StatCard({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="panel" style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 20px" }}>
      <div
        style={{
          width: 44, height: 44, borderRadius: "var(--radius-md)",
          background: color || "var(--primary-soft)",
          display: "grid", placeItems: "center", flexShrink: 0,
        }}
      >
        <Icon size={20} style={{ color: "var(--primary)" }} />
      </div>
      <div>
        <p style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{value}</p>
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 3 }}>{label}</p>
        {sub && <p style={{ fontSize: 11, color: "var(--success)", marginTop: 2 }}>{sub}</p>}
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--line)",
      borderRadius: "var(--radius)", padding: "10px 14px", fontSize: 13,
    }}>
      <p style={{ fontWeight: 600, marginBottom: 6, color: "var(--text)" }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color, margin: "2px 0" }}>
          {p.name}: <strong>{p.name === "Revenue" ? fmt(p.value) : p.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ── component ──────────────────────────────────────────────────────────────────

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-01-01`;
  });
  const [toDate, setToDate] = useState(() => new Date().toISOString().slice(0, 10));
  const { notify } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/analytics/overview", {
        params: { from_date: fromDate, to_date: toDate },
      });
      setData(res.data);
    } catch {
      notify("Failed to load analytics.", "error");
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, notify]);

  useEffect(() => { load(); }, [load]);

  // ── Derived chart data ─────────────────────────────────────────────────────

  const branchRevenueData = data?.branches.map((b) => ({
    name: b.branch_name,
    Revenue: b.revenue,
    Patients: b.patients,
    Leads: b.leads,
  })) ?? [];

  const appointmentPieData = data?.branches.reduce((acc, b) => {
    const appts = b.appointments;
    ["pending", "confirmed", "completed", "cancelled"].forEach((s) => {
      const existing = acc.find((x) => x.name === s);
      if (existing) existing.value += appts[s] || 0;
      else acc.push({ name: s, value: appts[s] || 0 });
    });
    return acc;
  }, []).filter((x) => x.value > 0) ?? [];

  const PIE_COLORS = {
    completed: "var(--success)",
    confirmed: "var(--primary)",
    pending: "#f59e0b",
    cancelled: "var(--danger)",
  };

  const trendData = data?.trend.map((t) => ({
    month: t.month,
    Revenue: t.revenue,
    Leads: t.leads,
  })) ?? [];

  return (
    <AppLayout
      title="Analytics"
      subtitle="Revenue, patients, and lead performance across all branches."
    >
      {/* Date filter */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 20, flexWrap: "wrap" }}>
        <div className="field" style={{ margin: 0 }}>
          <label style={{ fontSize: 12 }}>From</label>
          <input className="input" type="date" value={fromDate}
            onChange={(e) => setFromDate(e.target.value)} style={{ width: 150 }} />
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label style={{ fontSize: 12 }}>To</label>
          <input className="input" type="date" value={toDate}
            onChange={(e) => setToDate(e.target.value)} style={{ width: 150 }} />
        </div>
        <button className="btn btn-primary" onClick={load} disabled={loading}
          style={{ alignSelf: "flex-end" }}>
          <RefreshCw size={15} style={loading ? { animation: "spin 1s linear infinite" } : {}} />
          {loading ? "Loading…" : "Apply"}
        </button>
      </div>

      {loading && !data ? (
        <div className="empty-state"><p>Loading analytics…</p></div>
      ) : !data ? null : (
        <>
          {/* ── KPI cards ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14, marginBottom: 24 }}>
            <StatCard label="Total Revenue" value={fmt(data.totals.revenue)} icon={TrendingUp} />
            <StatCard label="Total Patients" value={data.totals.patients.toLocaleString()} icon={Users} />
            <StatCard label="Total Leads" value={data.totals.leads.toLocaleString()} icon={PhoneCall} />
            <StatCard
              label="Lead Conversion"
              value={`${data.totals.conversion_rate}%`}
              sub={`${data.totals.leads_converted} converted`}
              icon={UserCheck}
            />
          </div>

          {/* ── Revenue per branch bar chart ── */}
          <div className="panel" style={{ marginBottom: 20, padding: "20px 20px 10px" }}>
            <h3 style={{ marginBottom: 16 }}>Revenue per Branch</h3>
            {branchRevenueData.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: 13 }}>No revenue data in this period.</p>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={branchRevenueData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--muted)" }} />
                  <YAxis tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "var(--muted)" }} width={70} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="Revenue" radius={[4, 4, 0, 0]}>
                    {branchRevenueData.map((_, i) => (
                      <Cell key={i} fill={BRANCH_COLORS[i % BRANCH_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* ── Row: trend + pie ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16, marginBottom: 20 }}>
            {/* Monthly trend */}
            <div className="panel" style={{ padding: "20px 20px 10px" }}>
              <h3 style={{ marginBottom: 16 }}>Monthly Trend</h3>
              {trendData.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: 13 }}>No trend data.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={trendData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                    <YAxis yAxisId="rev" tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "var(--muted)" }} width={70} />
                    <YAxis yAxisId="leads" orientation="right" tick={{ fontSize: 11, fill: "var(--muted)" }} width={30} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line yAxisId="rev" type="monotone" dataKey="Revenue" stroke="var(--primary)" strokeWidth={2} dot={false} />
                    <Line yAxisId="leads" type="monotone" dataKey="Leads" stroke="#6366f1" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Appointment pie */}
            <div className="panel" style={{ padding: "20px 20px 10px" }}>
              <h3 style={{ marginBottom: 16 }}>Appointments by Status</h3>
              {appointmentPieData.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: 13 }}>No appointment data.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={appointmentPieData}
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={85}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, value }) => `${name} (${value})`}
                      labelLine={false}
                    >
                      {appointmentPieData.map((entry) => (
                        <Cell key={entry.name} fill={PIE_COLORS[entry.name] || "var(--muted)"} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* ── Branch comparison table ── */}
          <div className="panel">
            <div className="panel-header">
              <h3>Branch Comparison</h3>
            </div>
            <table className="responsive-table">
              <thead>
                <tr>
                  {["Branch", "Revenue", "Patients", "Leads", "Converted", "Conversion %",
                    "Pending", "Confirmed", "Completed"].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.branches.map((b, i) => (
                  <tr key={b.branch_id}>
                    <td data-label="Branch">
                      <span style={{
                        display: "inline-block", width: 10, height: 10,
                        borderRadius: "50%", background: BRANCH_COLORS[i % BRANCH_COLORS.length],
                        marginRight: 8,
                      }} />
                      <strong>{b.branch_name}</strong>
                    </td>
                    <td data-label="Revenue">{fmt(b.revenue)}</td>
                    <td data-label="Patients">{b.patients}</td>
                    <td data-label="Leads">{b.leads}</td>
                    <td data-label="Converted">{b.leads_converted}</td>
                    <td data-label="Conversion %">
                      <span className={`badge ${b.conversion_rate >= 50 ? "badge-success" : ""}`}>
                        {b.conversion_rate}%
                      </span>
                    </td>
                    <td data-label="Pending">{b.appointments.pending}</td>
                    <td data-label="Confirmed">{b.appointments.confirmed}</td>
                    <td data-label="Completed">{b.appointments.completed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </AppLayout>
  );
}
