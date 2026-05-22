import { useCallback, useEffect, useState } from "react";
import { Edit3, Plus } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const emptyForm = {
  name: "",
  slug: "",
  city: "",
  address: "",
  phone: "",
  bot_name: "",
  welcome_message: "",
};

export default function Branches() {
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState(null);
  const { notify } = useToast();

  const fetchBranches = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/branches");
      setBranches(res.data);
    } catch {
      notify("Failed to load branches.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchBranches();
  }, [fetchBranches]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditId(null);
  };

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const saveBranch = async (e) => {
    e.preventDefault();
    try {
      if (editId) {
        await api.put(`/branches/${editId}`, {
          name: form.name,
          city: form.city || null,
          address: form.address || null,
          phone: form.phone || null,
          bot_name: form.bot_name || null,
          welcome_message: form.welcome_message || null,
        });
        notify("Branch updated.", "success");
      } else {
        await api.post("/branches", {
          ...form,
          bot_name: form.bot_name || null,
          welcome_message: form.welcome_message || null,
        });
        notify("Branch created.", "success");
      }
      resetForm();
      setShowForm(false);
      fetchBranches();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to save branch.", "error");
    }
  };

  const editBranch = (b) => {
    setEditId(b.id);
    setForm({
      name: b.name,
      slug: b.slug,
      city: b.city || "",
      address: b.address || "",
      phone: b.phone || "",
      bot_name: b.bot_name || "",
      welcome_message: b.welcome_message || "",
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const toggleBranch = async (b) => {
    if (!window.confirm(`${b.is_active ? "Deactivate" : "Activate"} branch "${b.name}"?`)) return;
    try {
      await api.patch(`/branches/${b.id}/toggle`);
      notify("Branch status updated.", "success");
      fetchBranches();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to update branch.", "error");
    }
  };

  return (
    <AppLayout
      title="Branches"
      subtitle="Manage clinic locations. Each branch has its own chatbot embed slug."
      actions={
        <button
          className="btn btn-primary"
          onClick={() => { resetForm(); setShowForm((s) => !s); }}
        >
          <Plus size={16} />
          {showForm && !editId ? "Close" : "Add branch"}
        </button>
      }
    >
      {showForm && (
        <section className="form-panel">
          <h2>{editId ? "Edit branch" : "New branch"}</h2>
          <form onSubmit={saveBranch} className="form-stack">
            <div className="form-grid">
              <input
                className="input"
                placeholder="Branch name *"
                value={form.name}
                onChange={set("name")}
                required
              />
              <input
                className="input"
                placeholder="Slug e.g. karachi-main *"
                value={form.slug}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
                  }))
                }
                required
                disabled={!!editId}
                title={editId ? "Slug cannot be changed after creation" : ""}
              />
              <input className="input" placeholder="City" value={form.city} onChange={set("city")} />
              <input className="input" placeholder="Phone" value={form.phone} onChange={set("phone")} />
            </div>
            <input className="input" placeholder="Address" value={form.address} onChange={set("address")} />
            <input
              className="input"
              placeholder="Bot name — overrides clinic default"
              value={form.bot_name}
              onChange={set("bot_name")}
            />
            <textarea
              className="input textarea"
              placeholder="Welcome message — overrides clinic default"
              value={form.welcome_message}
              onChange={set("welcome_message")}
            />
            <div className="action-row">
              <button className="btn btn-primary" type="submit">
                {editId ? "Save changes" : "Create branch"}
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => { resetForm(); setShowForm(false); }}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Branches</h2>
          <span className="badge">{branches.length} total</span>
        </div>
        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : branches.length === 0 ? (
          <EmptyState
            title="No branches yet"
            description="Your clinic was set up with a default main branch. Add more locations here."
            action={<button className="btn btn-primary" onClick={() => setShowForm(true)}>Add branch</button>}
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>
                {["Branch", "Slug / Embed ID", "City", "Phone", "Bot name", "Status", "Actions"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {branches.map((b) => (
                <tr key={b.id}>
                  <td data-label="Branch">
                    <strong>{b.name}</strong>
                    {b.is_main_branch && (
                      <span className="badge badge-success" style={{ marginLeft: 6, fontSize: 11 }}>main</span>
                    )}
                  </td>
                  <td data-label="Slug / Embed ID">
                    <code style={{ fontSize: 12 }}>{b.slug}</code>
                  </td>
                  <td data-label="City">{b.city || "—"}</td>
                  <td data-label="Phone">{b.phone || "—"}</td>
                  <td data-label="Bot name">
                    {b.bot_name || <span style={{ color: "var(--muted)" }}>clinic default</span>}
                  </td>
                  <td data-label="Status">
                    <span className={`badge ${b.is_active ? "badge-success" : "badge-danger"}`}>
                      {b.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td data-label="Actions">
                    <div className="action-row" style={{ justifyContent: "flex-end" }}>
                      <button className="icon-btn" onClick={() => editBranch(b)} title="Edit branch">
                        <Edit3 size={15} />
                      </button>
                      <button
                        className={b.is_active ? "btn btn-danger" : "btn btn-primary"}
                        style={{ fontSize: 12, padding: "4px 10px" }}
                        onClick={() => toggleBranch(b)}
                      >
                        {b.is_active ? "Deactivate" : "Activate"}
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
