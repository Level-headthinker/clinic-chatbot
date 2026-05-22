import { useCallback, useEffect, useState } from "react";
import { CheckCircle, Clock, Plus, Trash2 } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const STATUSES = ["pending", "done", "cancelled"];

const emptyForm = {
  title: "",
  notes: "",
  due_date: "",
  patient_id: "",
  lead_id: "",
};

function statusBadge(s) {
  if (s === "done") return "badge-success";
  if (s === "cancelled") return "badge-danger";
  return "badge-warning";
}

function isOverdue(due, status) {
  return status === "pending" && new Date(due) < new Date();
}

export default function FollowUps() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("pending");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const { notify } = useToast();

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = filterStatus ? { status: filterStatus } : {};
      const res = await api.get("/follow-ups", { params });
      setItems(res.data);
    } catch {
      notify("Failed to load follow-ups.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify, filterStatus]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const createFollowUp = async (e) => {
    e.preventDefault();
    try {
      await api.post("/follow-ups", {
        ...form,
        patient_id: form.patient_id || null,
        lead_id: form.lead_id || null,
        due_date: new Date(form.due_date).toISOString(),
      });
      notify("Follow-up created.", "success");
      setForm(emptyForm);
      setShowForm(false);
      fetchItems();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to create follow-up.", "error");
    }
  };

  const markDone = async (id) => {
    try {
      await api.patch(`/follow-ups/${id}/done`);
      notify("Marked as done.", "success");
      fetchItems();
    } catch {
      notify("Failed to update.", "error");
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this follow-up?")) return;
    try {
      await api.delete(`/follow-ups/${id}`);
      notify("Deleted.", "success");
      fetchItems();
    } catch {
      notify("Failed to delete.", "error");
    }
  };

  const pending = items.filter((i) => i.status === "pending").length;
  const overdue = items.filter((i) => isOverdue(i.due_date, i.status)).length;

  return (
    <AppLayout
      title="Follow-ups"
      subtitle="Track tasks, reminders, and patient follow-up actions."
      actions={
        <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
          <Plus size={16} />
          {showForm ? "Close" : "New follow-up"}
        </button>
      }
    >
      {showForm && (
        <section className="form-panel">
          <h2>New follow-up</h2>
          <form onSubmit={createFollowUp} className="form-stack">
            <div className="form-grid">
              <input
                className="input"
                placeholder="Title *"
                value={form.title}
                onChange={set("title")}
                required
              />
              <input
                className="input"
                type="datetime-local"
                value={form.due_date}
                onChange={set("due_date")}
                required
              />
            </div>
            <textarea
              className="input textarea"
              placeholder="Notes (optional)"
              value={form.notes}
              onChange={set("notes")}
            />
            <div className="form-grid">
              <input
                className="input"
                placeholder="Patient ID (optional)"
                value={form.patient_id}
                onChange={set("patient_id")}
              />
              <input
                className="input"
                placeholder="Lead ID (optional)"
                value={form.lead_id}
                onChange={set("lead_id")}
              />
            </div>
            <p style={{ fontSize: 12, color: "var(--muted)" }}>
              Tip: open a patient or lead record and copy the ID from the URL.
            </p>
            <div className="action-row">
              <button className="btn btn-primary" type="submit">Create</button>
              <button className="btn btn-secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </section>
      )}

      {/* Summary chips */}
      {!loading && (
        <div className="metric-grid" style={{ marginBottom: 0 }}>
          <div className="stat-chip stat-chip--warning">
            <Clock size={14} className="stat-chip-icon" />
            <span className="stat-chip-value">{pending}</span>
            <span className="stat-chip-label">Pending</span>
          </div>
          <div className="stat-chip stat-chip--neutral" style={{ borderColor: overdue > 0 ? "var(--danger)" : undefined }}>
            <span className="stat-chip-value" style={{ color: overdue > 0 ? "var(--danger)" : undefined }}>{overdue}</span>
            <span className="stat-chip-label">Overdue</span>
          </div>
        </div>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Follow-ups</h2>
          <div className="action-row">
            {["", ...STATUSES].map((s) => (
              <button
                key={s || "all"}
                className={`btn ${filterStatus === s ? "btn-primary" : "btn-secondary"}`}
                style={{ fontSize: 12, padding: "4px 10px" }}
                onClick={() => setFilterStatus(s)}
              >
                {s || "All"}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : items.length === 0 ? (
          <EmptyState
            title="No follow-ups"
            description="Create a follow-up to track tasks and reminders for patients or leads."
            action={<button className="btn btn-primary" onClick={() => setShowForm(true)}>New follow-up</button>}
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>
                {["Title", "Due date", "Status", "Notes", "Actions"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} style={{ opacity: item.status !== "pending" ? 0.6 : 1 }}>
                  <td data-label="Title">
                    <strong>{item.title}</strong>
                    {isOverdue(item.due_date, item.status) && (
                      <span className="badge badge-danger" style={{ marginLeft: 6, fontSize: 10 }}>overdue</span>
                    )}
                  </td>
                  <td data-label="Due date">
                    {new Date(item.due_date).toLocaleString()}
                  </td>
                  <td data-label="Status">
                    <span className={`badge ${statusBadge(item.status)}`}>{item.status}</span>
                  </td>
                  <td data-label="Notes" style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.notes || "—"}
                  </td>
                  <td data-label="Actions">
                    <div className="action-row" style={{ justifyContent: "flex-end" }}>
                      {item.status === "pending" && (
                        <button className="icon-btn" title="Mark done" onClick={() => markDone(item.id)}>
                          <CheckCircle size={15} />
                        </button>
                      )}
                      <button className="icon-btn btn-danger" title="Delete" onClick={() => remove(item.id)}>
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
