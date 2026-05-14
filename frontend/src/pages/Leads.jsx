import { useCallback, useEffect, useState } from "react";
import { Download, MessageCircle, Trash2, Upload } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const { notify } = useToast();

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const url = filter
        ? `/leads/?status=${encodeURIComponent(filter)}`
        : "/leads/";
      const res = await api.get(url);
      setLeads(res.data);
    } catch {
      notify("Failed to load leads.", "error");
    } finally {
      setLoading(false);
    }
  }, [filter, notify]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get("/leads/stats");
      setStats(res.data);
    } catch {
      notify("Failed to load lead stats.", "error");
    }
  }, [notify]);

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [fetchLeads, fetchStats]);

  const updateStatus = async (id, status) => {
    try {
      await api.put(`/leads/${id}`, { status });
      await Promise.all([fetchLeads(), fetchStats()]);
      notify("Lead status updated.", "success");
    } catch {
      notify("Failed to update lead status.", "error");
    }
  };

  const deleteLead = async (id) => {
    if (!window.confirm("Remove this lead?")) return;
    try {
      await api.delete(`/leads/${id}`);
      await Promise.all([fetchLeads(), fetchStats()]);
      notify("Lead removed.", "success");
    } catch {
      notify("Failed to remove lead.", "error");
    }
  };

  const normalizeWhatsAppPhone = (phone) => {
    const digits = String(phone || "").replace(/\D/g, "");
    if (digits.startsWith("0")) return `92${digits.slice(1)}`;
    return digits;
  };

  const openWhatsApp = (phone, name) => {
    const whatsappPhone = normalizeWhatsAppPhone(phone);
    if (!whatsappPhone) {
      notify("This lead does not have a valid phone number.", "error");
      return;
    }

    const message = encodeURIComponent(
      `Assalam o Alaikum ${name} ji, City Clinic ki taraf se message hai. ` +
      "Aap ne hamare chatbot se appointment ki inquiry ki thi. " +
      "Kya aap appointment book karna chahte hain? Reply karein ya call karein. Shukriya!"
    );
    window.open(`https://wa.me/${whatsappPhone}?text=${message}`, "_blank");
  };

  const handleImport = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setImporting(true);
    setImportResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.post("/leads/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(res.data);
      await Promise.all([fetchLeads(), fetchStats()]);
      notify("Patient import completed.", "success");
    } catch (err) {
      notify(err.response?.data?.detail || "Import failed. Check your CSV format.", "error");
    } finally {
      setImporting(false);
      event.target.value = "";
    }
  };

  const downloadTemplate = () => {
    window.open(`${api.defaults.baseURL}/leads/import-template`, "_blank");
  };

  return (
    <AppLayout
      title="Leads"
      subtitle="Follow up with every patient captured by the chatbot."
      actions={
        <>
          <select className="select" value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="">All leads</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>
          <button className="btn btn-secondary" onClick={downloadTemplate}>
            <Download size={16} />
            Template
          </button>
          <label className="btn btn-primary">
            <Upload size={16} />
            {importing ? "Importing..." : "Import CSV"}
            <input type="file" accept=".csv" onChange={handleImport} style={{ display: "none" }} />
          </label>
        </>
      }
    >
      {stats && (
        <div className="metric-grid">
          <Metric label="Total" value={stats.total} />
          <Metric label="New" value={stats.new} />
          <Metric label="Converted" value={stats.converted} />
          <Metric label="Conversion" value={stats.conversion_rate} />
        </div>
      )}

      {importResult && (
        <div className="demo-card" style={{ marginBottom: 16 }}>
          <strong>Import complete:</strong> {importResult.imported} patients added,{" "}
          {importResult.skipped} skipped.
        </div>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Patient inquiries</h2>
          <span className="badge">{leads.length} visible</span>
        </div>

        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : leads.length === 0 ? (
          <EmptyState
            title="No leads in this view"
            description="New chatbot inquiries will appear here with patient phone numbers and follow-up status."
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>
                {["Name", "Phone", "Concern", "Status", "Date", "Actions"].map((heading) => (
                  <th key={heading}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td data-label="Name">{lead.name}</td>
                  <td data-label="Phone">{lead.phone}</td>
                  <td data-label="Concern">{trimConcern(lead.concern)}</td>
                  <td data-label="Status">
                    <select
                      className="select"
                      value={lead.status}
                      onChange={(event) => updateStatus(lead.id, event.target.value)}
                    >
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="converted">Converted</option>
                      <option value="lost">Lost</option>
                    </select>
                  </td>
                  <td data-label="Date">{new Date(lead.created_at).toLocaleDateString()}</td>
                  <td data-label="Actions">
                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                      <button
                        className="icon-btn"
                        onClick={() => openWhatsApp(lead.phone, lead.name)}
                        title="Send WhatsApp"
                      >
                        <MessageCircle size={16} />
                      </button>
                      <button
                        className="icon-btn btn-danger"
                        onClick={() => deleteLead(lead.id)}
                        title="Remove lead"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </AppLayout>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-card">
      <div>
        <p className="metric-label">{label}</p>
        <p className="metric-value">{value}</p>
      </div>
    </div>
  );
}

function trimConcern(concern) {
  if (!concern) return "-";
  return concern.length > 64 ? `${concern.slice(0, 64)}...` : concern;
}
