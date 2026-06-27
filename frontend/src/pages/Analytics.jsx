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
import {
  Users, UserCheck, PhoneCall, RefreshCw, Calendar,
  Wallet, AlertCircle,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useToast } from "../context/ToastContext";

// ── helpers ────────────────────────────────────────────────────────────────────

function fmt(n) {
  const v = Number(n) || 0;
  if (v >= 1_000_000) return `Rs ${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `Rs ${(v / 1_000).toFixed(1)}K`;
  return `Rs ${v.toLocaleString()}`;
}

const ymd = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const PRESETS = [
  { label: "This month", range: () => { const d = new Date(); return [ymd(new Date(d.getFullYear(), d.getMonth(), 1)), ymd(d)]; } },
  { label: "Last 30 days", range: () => { const d = new Date(); const s = new Date(); s.setDate(d.getDate() - 29); return [ymd(s), ymd(d)]; } },
  { label: "This year", range: () => { const d = new Date(); return [ymd(new Date(d.getFullYear(), 0, 1)), ymd(d)]; } },
  { label: "Last 12 months", range: () => { const d = new Date(); const s = new Date(); s.setFullYear(d.getFullYear() - 1); return [ymd(s), ymd(d)]; } },
];

const BRANCH_COLORS = [
  "var(--primary)", "#6366f1", "#f59e0b", "#10b981", "#ef4444",
  "#8b5cf6", "#06b6d4", "#f97316",
];

const fmtMonth = (m) => {
  // "2026-06" → "Jun '26"
  const [y, mo] = (m || "").split("-");
  if (!y || !mo) return m;
  const name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][parseInt(mo) - 1];
  return `${name} '${y.slice(2)}`;
};

function StatCard({ label, value, sub, icon: Icon, accent = "var(--primary)", tint = "var(--primary-soft)" }) {
  return (
    <div className="panel" style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 18px" }}>
      <div style={{
        width: 44, height: 44, borderRadius: "var(--radius-md, 12px)",
        background: tint, display: "grid", placeItems: "center", flexShrink: 0,
      }}>
        <Icon size={20} style={{ color: accent }} />
      </div>
      <div style={{ minWidth: 0 }}>
        <p style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", lineHeight: 1.1 }}>{value}</p>
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 3 }}>{label}</p>
        {sub && <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{sub}</p>}
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
      boxShadow: "0 6px 24px rgba(0,0,0,.12)",
    }}>
      <p style={{ fontWeight: 600, marginBottom: 6, color: "var(--text)" }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color, margin: "2px 0" }}>
          {p.name}: <strong>{["Revenue", "Collected", "Billed"].includes(p.name) ? fmt(p.value) : p.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ── component ──────────────────────────────────────────────────────────────────

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activePreset, setActivePreset] = useState("This year");
  const [fromDate, setFromDate] = useState(() => `${new Date().getFullYear()}-01-01`);
  const [toDate, setToDate] = useState(() => ymd(new Date()));
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

  const applyPreset = (preset) => {
    const [f, t] = preset.range();
    setActivePreset(preset.label);
    setFromDate(f);
    setToDate(t);
  };

  // ── Derived chart data ─────────────────────────────────────────────────────
  const t = data?.totals;

  const branchRevenueData = data?.branches.map((b) => ({
    name: b.branch_name,
    Collected: b.collected ?? b.revenue,
    Billed: b.billed ?? b.revenue,
  })) ?? [];

  const STATUS_ORDER = ["completed", "confirmed", "checked_in", "in_progress", "pending", "no_show", "cancelled"];
  const appointmentPieData = (data?.branches.reduce((acc, b) => {
    STATUS_ORDER.forEach((s) => {
      const existing = acc.find((x) => x.name === s);
      const val = b.appointments[s] || 0;
      if (existing) existing.value += val;
      else acc.push({ name: s, value: val });
    });
    return acc;
  }, []) ?? []).filter((x) => x.value > 0);

  const PIE_COLORS = {
    completed: "var(--success, #16a34a)",
    confirmed: "var(--primary)",
    checked_in: "#06b6d4",
    in_progress: "#8b5cf6",
    pending: "#f59e0b",
    no_show: "#ef4444",
    cancelled: "#9ca3af",
  };
  const STATUS_LABEL = {
    completed: "Completed", confirmed: "Confirmed", checked_in: "Checked in",
    in_progress: "In progress", pending: "Pending", no_show: "No-show", cancelled: "Cancelled",
  };

  const trendData = data?.trend.map((m) => ({
    month: fmtMonth(m.month),
    Revenue: m.revenue,
    Leads: m.leads,
  })) ?? [];

  return (
    <AppLayout
      title="Analytics"
      subtitle="Revenue, patients, appointments, and lead performance across all branches."
    >
      {/* Date filter + presets */}
      <div className="panel" style={{ padding: "14px 16px", marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {PRESETS.map((p) => (
              <button
                key={p.label}
                className={`btn ${activePreset === p.label ? "btn-primary" : "btn-secondary"}`}
                style={{ fontSize: 12, padding: "7px 12px" }}
                onClick={() => applyPreset(p)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div style={{ flex: 1 }} />
          <div className="field" style={{ margin: 0 }}>
            <label style={{ fontSize: 11 }}>From</label>
            <input className="input" type="date" value={fromDate}
              onChange={(e) => { setActivePreset(null); setFromDate(e.target.value); }} style={{ width: 150 }} />
          </div>
          <div className="field" style={{ margin: 0 }}>
            <label style={{ fontSize: 11 }}>To</label>
            <input className="input" type="date" value={toDate}
              onChange={(e) => { setActivePreset(null); setToDate(e.target.value); }} style={{ width: 150 }} />
          </div>
          <button className="btn btn-secondary" onClick={load} disabled={loading} title="Refresh">
            <RefreshCw size={15} style={loading ? { animation: "spin 1s linear infinite" } : {}} />
          </button>
        </div>
      </div>

      {loading && !data ? (
        <div className="empty-state"><p>Loading analytics…</p></div>
      ) : !data ? null : (
        <>
          {/* ── KPI cards ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 14, marginBottom: 22 }}>
            <StatCard
              label="Revenue collected" value={fmt(t.collected ?? t.revenue)}
              sub={`${t.collection_rate ?? 0}% of ${fmt(t.billed ?? 0)} billed`}
              icon={Wallet} accent="var(--primary)" tint="var(--primary-soft, rgba(13,148,136,.1))"
            />
            <StatCard
              label="Outstanding" value={fmt(t.outstanding ?? 0)}
              sub="Billed but not yet paid"
              icon={AlertCircle} accent="#f59e0b" tint="rgba(245,158,11,.12)"
            />
            <StatCard
              label="Patients" value={(t.patients ?? 0).toLocaleString()}
              sub="New in this period"
              icon={Users} accent="#6366f1" tint="rgba(99,102,241,.12)"
            />
            <StatCard
              label="Appointments" value={(t.appointments ?? 0).toLocaleString()}
              sub={`${t.completion_rate ?? 0}% completed · ${t.appointments_no_show ?? 0} no-show`}
              icon={Calendar} accent="#06b6d4" tint="rgba(6,182,212,.12)"
            />
            <StatCard
              label="Leads" value={(t.leads ?? 0).toLocaleString()}
              sub={`${t.leads_converted ?? 0} converted`}
              icon={PhoneCall} accent="#8b5cf6" tint="rgba(139,92,246,.12)"
            />
            <StatCard
              label="Lead conversion" value={`${t.conversion_rate ?? 0}%`}
              sub="Leads that became patients"
              icon={UserCheck} accent="#16a34a" tint="rgba(22,163,74,.12)"
            />
          </div>

          {/* ── Revenue per branch: collected vs billed ── */}
          <div className="panel" style={{ marginBottom: 18, padding: "20px 20px 10px" }}>
            <h3 style={{ marginBottom: 4 }}>Revenue per branch</h3>
            <p style={{ margin: "0 0 14px", fontSize: 12, color: "var(--muted)" }}>Collected vs total billed.</p>
            {branchRevenueData.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: 13 }}>No revenue data in this period.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={branchRevenueData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--muted)" }} />
                  <YAxis tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "var(--muted)" }} width={70} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,.03)" }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Billed" fill="var(--line)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Collected" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* ── Row: trend + pie ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16, marginBottom: 18 }}>
            {/* Monthly trend */}
            <div className="panel" style={{ padding: "20px 20px 10px" }}>
              <h3 style={{ marginBottom: 16 }}>Monthly trend</h3>
              {trendData.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: 13 }}>No trend data.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={trendData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                    <YAxis yAxisId="rev" tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "var(--muted)" }} width={64} />
                    <YAxis yAxisId="leads" orientation="right" tick={{ fontSize: 11, fill: "var(--muted)" }} width={30} allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line yAxisId="rev" type="monotone" dataKey="Revenue" stroke="var(--primary)" strokeWidth={2.5} dot={false} />
                    <Line yAxisId="leads" type="monotone" dataKey="Leads" stroke="#8b5cf6" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Appointment pie */}
            <div className="panel" style={{ padding: "20px 20px 10px" }}>
              <h3 style={{ marginBottom: 16 }}>Appointments by status</h3>
              {appointmentPieData.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: 13 }}>No appointment data.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={appointmentPieData}
                      cx="50%" cy="50%"
                      innerRadius={58} outerRadius={88}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {appointmentPieData.map((entry) => (
                        <Cell key={entry.name} fill={PIE_COLORS[entry.name] || "var(--muted)"} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value, name) => [value, STATUS_LABEL[name] || name]} />
                    <Legend
                      wrapperStyle={{ fontSize: 12 }}
                      formatter={(value) => STATUS_LABEL[value] || value}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* ── Branch comparison table ── */}
          <div className="panel">
            <div className="panel-header">
              <h3>Branch comparison</h3>
              <span className="badge">{data.branches.length} branch{data.branches.length === 1 ? "" : "es"}</span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="responsive-table">
                <thead>
                  <tr>
                    {["Branch", "Collected", "Outstanding", "Patients", "Leads", "Conv. %",
                      "Appts", "Completed", "No-show"].map((h) => (
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
                      <td data-label="Collected">{fmt(b.collected ?? b.revenue)}</td>
                      <td data-label="Outstanding" style={{ color: (b.outstanding ?? 0) > 0 ? "#f59e0b" : "inherit" }}>
                        {fmt(b.outstanding ?? 0)}
                      </td>
                      <td data-label="Patients">{b.patients}</td>
                      <td data-label="Leads">{b.leads}</td>
                      <td data-label="Conv. %">
                        <span className={`badge ${b.conversion_rate >= 50 ? "badge-success" : ""}`}>
                          {b.conversion_rate}%
                        </span>
                      </td>
                      <td data-label="Appts">{b.appointments.total ?? 0}</td>
                      <td data-label="Completed">{b.appointments.completed}</td>
                      <td data-label="No-show" style={{ color: b.appointments.no_show > 0 ? "#ef4444" : "inherit" }}>
                        {b.appointments.no_show ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}
