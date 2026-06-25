import { useCallback, useEffect, useState } from "react";
import { Download, Trash2, RotateCcw, History, Shield } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useToast } from "../context/ToastContext";

const ACTION_STYLE = {
  create:  { label: "Created",  color: "#0d9488" },
  update:  { label: "Updated",  color: "#2563eb" },
  delete:  { label: "Deleted",  color: "#ef4444" },
  restore: { label: "Restored", color: "#16a34a" },
  export:  { label: "Exported", color: "#7c3aed" },
};

function ActionBadge({ action }) {
  const a = ACTION_STYLE[action] || { label: action, color: "#6b7280" };
  return (
    <span style={{
      background: a.color, color: "#fff", borderRadius: 8,
      fontSize: 11, fontWeight: 700, padding: "2px 8px", whiteSpace: "nowrap",
    }}>{a.label}</span>
  );
}

export default function DataPrivacy() {
  const { notify } = useToast();
  const [exporting, setExporting] = useState(false);
  const [trash, setTrash] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, l] = await Promise.all([
        api.get("/patients/trash/list"),
        api.get("/audit-logs/", { params: { limit: 50 } }),
      ]);
      setTrash(t.data || []);
      setLogs(l.data?.items || []);
    } catch {
      notify("Failed to load data & privacy info.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { load(); }, [load]);

  const exportData = async () => {
    setExporting(true);
    try {
      const res = await api.get("/export/my-data", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      // Pull filename from Content-Disposition when present.
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^"]+)"?/);
      a.download = match ? match[1] : "clinic_export.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      notify("Your data export has downloaded.", "success");
      load(); // refresh the activity log (export is recorded)
    } catch {
      notify("Export failed. Please try again.", "error");
    } finally {
      setExporting(false);
    }
  };

  const restore = async (id, name) => {
    try {
      await api.post(`/patients/${id}/restore`);
      notify(`Restored ${name}.`, "success");
      setTrash((rows) => rows.filter((r) => r.id !== id));
      load();
    } catch {
      notify("Restore failed.", "error");
    }
  };

  return (
    <AppLayout
      title="Data & Privacy"
      subtitle="Export your clinic's data, recover deleted records, and review activity."
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* Export my data */}
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Download size={18} style={{ color: "var(--primary)" }} />
              <h3>Export my data</h3>
            </div>
          </div>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 14px", maxWidth: 620 }}>
            Download a complete copy of your clinic's records — patients, appointments,
            visits, invoices, leads, conversations and more — as a ZIP of CSV files
            (open them in Excel). Your data is always yours.
          </p>
          <button className="btn btn-primary" onClick={exportData} disabled={exporting}>
            <Download size={15} />
            {exporting ? "Preparing…" : "Download my data (.zip)"}
          </button>
        </div>

        {/* Recently deleted (trash bin) */}
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Trash2 size={18} style={{ color: "#ef4444" }} />
              <h3>Recently deleted patients</h3>
            </div>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              {trash.length} in trash
            </span>
          </div>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 14px", maxWidth: 620 }}>
            Deleted patients aren't erased — they're kept here so you can recover them
            if a delete was a mistake.
          </p>
          {loading ? (
            <p style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</p>
          ) : trash.length === 0 ? (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
              ✅ Nothing in trash — no deleted patients.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="responsive-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Deleted</th>
                    <th style={{ textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {trash.map((p) => (
                    <tr key={p.id}>
                      <td data-label="Name">{p.name}</td>
                      <td data-label="Phone">{p.phone}</td>
                      <td data-label="Deleted" style={{ color: "var(--muted)" }}>
                        {p.deleted_at ? new Date(p.deleted_at).toLocaleString() : "—"}
                      </td>
                      <td data-label="" style={{ textAlign: "right" }}>
                        <button className="btn btn-secondary" onClick={() => restore(p.id, p.name)}>
                          <RotateCcw size={14} /> Restore
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Activity / audit log */}
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <History size={18} style={{ color: "var(--primary)" }} />
              <h3>Activity log</h3>
            </div>
            <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--muted)" }}>
              <Shield size={13} /> Tamper-evident trail
            </span>
          </div>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 14px", maxWidth: 620 }}>
            A record of who changed, deleted, restored or exported data — so nothing
            happens to patient records without a trace.
          </p>
          {loading ? (
            <p style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</p>
          ) : logs.length === 0 ? (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
              No activity recorded yet.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="responsive-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Action</th>
                    <th>What</th>
                    <th>By</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((r) => (
                    <tr key={r.id}>
                      <td data-label="When" style={{ color: "var(--muted)", whiteSpace: "nowrap" }}>
                        {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                      </td>
                      <td data-label="Action"><ActionBadge action={r.action} /></td>
                      <td data-label="What">{r.summary || `${r.action} ${r.entity_type}`}</td>
                      <td data-label="By" style={{ color: "var(--muted)" }}>{r.user_email || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </AppLayout>
  );
}
