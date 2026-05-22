import { useCallback, useEffect, useState } from "react";
import { Edit3, Key, Plus } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";

const emptyCreate = { email: "", password: "", full_name: "", role: "staff", branch_id: "" };

export default function Users() {
  const [users, setUsers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyCreate);
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({ full_name: "", role: "staff", branch_id: "" });
  const [resetTarget, setResetTarget] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const { notify } = useToast();
  const { user: me } = useAuth();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [usersRes, branchesRes] = await Promise.all([
        api.get("/users"),
        api.get("/branches"),
      ]);
      setUsers(usersRes.data);
      setBranches(branchesRes.data);
    } catch {
      notify("Failed to load staff.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  const setEdit = (field) => (e) => setEditForm((f) => ({ ...f, [field]: e.target.value }));

  const createUser = async (e) => {
    e.preventDefault();
    try {
      await api.post("/users", { ...form, branch_id: form.branch_id || null });
      notify("Staff account created.", "success");
      setForm(emptyCreate);
      setShowForm(false);
      fetchData();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to create user.", "error");
    }
  };

  const startEdit = (u) => {
    setEditId(u.id);
    setEditForm({ full_name: u.full_name || "", role: u.role, branch_id: u.branch_id || "" });
    setShowForm(false);
    setResetTarget(null);
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/users/${editId}`, {
        full_name: editForm.full_name,
        role: editForm.role,
        branch_id: editForm.branch_id || null,
      });
      notify("User updated.", "success");
      setEditId(null);
      fetchData();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to update user.", "error");
    }
  };

  const toggleUser = async (u) => {
    if (!window.confirm(`${u.is_active ? "Deactivate" : "Activate"} "${u.full_name}"?`)) return;
    try {
      await api.patch(`/users/${u.id}/toggle`);
      notify("Status updated.", "success");
      fetchData();
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to update status.", "error");
    }
  };

  const submitResetPassword = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/users/${resetTarget.id}/reset-password`, { new_password: newPassword });
      notify("Password reset successfully.", "success");
      setResetTarget(null);
      setNewPassword("");
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to reset password.", "error");
    }
  };

  const openReset = (u) => {
    setResetTarget(u);
    setNewPassword("");
    setEditId(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <AppLayout
      title="Staff & Users"
      subtitle="Manage who can log in to the dashboard and which branches they can access."
      actions={
        <button
          className="btn btn-primary"
          onClick={() => { setShowForm((s) => !s); setEditId(null); setResetTarget(null); }}
        >
          <Plus size={16} />
          {showForm ? "Close" : "Add staff"}
        </button>
      }
    >
      {showForm && (
        <section className="form-panel">
          <h2>New staff account</h2>
          <form onSubmit={createUser} className="form-stack">
            <div className="form-grid">
              <input
                className="input"
                placeholder="Full name *"
                value={form.full_name}
                onChange={set("full_name")}
                required
              />
              <input
                className="input"
                type="email"
                placeholder="Email *"
                value={form.email}
                onChange={set("email")}
                required
              />
              <input
                className="input"
                type="password"
                placeholder="Password *"
                value={form.password}
                onChange={set("password")}
                required
              />
              <select className="select" value={form.role} onChange={set("role")}>
                <option value="staff">Staff</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="field">
              <label>Branch access</label>
              <select className="select" value={form.branch_id} onChange={set("branch_id")}>
                <option value="">All branches (tenant-level)</option>
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
              <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                Leave blank to grant access to all branches.
              </p>
            </div>
            <div className="action-row">
              <button className="btn btn-primary" type="submit">Create account</button>
              <button className="btn btn-secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </section>
      )}

      {resetTarget && (
        <section className="form-panel">
          <h2>Reset password — {resetTarget.full_name}</h2>
          <form onSubmit={submitResetPassword} className="form-stack">
            <input
              className="input"
              type="password"
              placeholder="New password *"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              style={{ maxWidth: 360 }}
            />
            <div className="action-row">
              <button className="btn btn-primary" type="submit">Set password</button>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => { setResetTarget(null); setNewPassword(""); }}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Staff accounts</h2>
          <span className="badge">{users.length} users</span>
        </div>
        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : users.length === 0 ? (
          <EmptyState
            title="No staff yet"
            description="Add team members so they can log in and manage the clinic dashboard."
            action={<button className="btn btn-primary" onClick={() => setShowForm(true)}>Add first staff</button>}
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>
                {["Name", "Email", "Role", "Branch", "Status", "Actions"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) =>
                editId === u.id ? (
                  <tr key={u.id}>
                    <td colSpan={6} style={{ padding: "12px 16px", background: "var(--bg)" }}>
                      <form onSubmit={saveEdit} className="form-stack" style={{ margin: 0 }}>
                        <div className="form-grid">
                          <input
                            className="input"
                            placeholder="Full name"
                            value={editForm.full_name}
                            onChange={setEdit("full_name")}
                            required
                          />
                          <select className="select" value={editForm.role} onChange={setEdit("role")}>
                            <option value="staff">Staff</option>
                            <option value="admin">Admin</option>
                          </select>
                          <select className="select" value={editForm.branch_id} onChange={setEdit("branch_id")}>
                            <option value="">All branches</option>
                            {branches.map((b) => (
                              <option key={b.id} value={b.id}>{b.name}</option>
                            ))}
                          </select>
                        </div>
                        <div className="action-row">
                          <button className="btn btn-primary" type="submit">Save</button>
                          <button className="btn btn-secondary" type="button" onClick={() => setEditId(null)}>Cancel</button>
                        </div>
                      </form>
                    </td>
                  </tr>
                ) : (
                  <tr key={u.id}>
                    <td data-label="Name">
                      <strong>{u.full_name}</strong>
                      {u.email === me?.email && (
                        <span className="badge badge-success" style={{ marginLeft: 6, fontSize: 11 }}>you</span>
                      )}
                    </td>
                    <td data-label="Email">{u.email}</td>
                    <td data-label="Role">
                      <span className={`badge ${u.role === "admin" ? "badge-success" : ""}`}>{u.role}</span>
                    </td>
                    <td data-label="Branch">
                      {u.branch_name || <span style={{ color: "var(--muted)" }}>All branches</span>}
                    </td>
                    <td data-label="Status">
                      <span className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}>
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td data-label="Actions">
                      <div className="action-row" style={{ justifyContent: "flex-end" }}>
                        <button className="icon-btn" onClick={() => startEdit(u)} title="Edit user">
                          <Edit3 size={15} />
                        </button>
                        <button className="icon-btn" onClick={() => openReset(u)} title="Reset password">
                          <Key size={15} />
                        </button>
                        {u.email !== me?.email && (
                          <button
                            className={u.is_active ? "btn btn-danger" : "btn btn-primary"}
                            style={{ fontSize: 12, padding: "4px 10px" }}
                            onClick={() => toggleUser(u)}
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </section>
    </AppLayout>
  );
}
