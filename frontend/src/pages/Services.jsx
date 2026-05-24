import { useCallback, useEffect, useState } from "react";
import { Edit2, Plus, Scissors, Trash2, X } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

// ── Modal ─────────────────────────────────────────────────────────────────────
function ServiceModal({ svc, onClose, onSave }) {
  const [form, setForm] = useState({
    name: svc?.name || "",
    duration_minutes: svc?.duration_minutes ?? 30,
    price: svc?.price ?? "",
  });
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        duration_minutes: Number(form.duration_minutes) || 30,
        price: form.price !== "" ? Number(form.price) : null,
      };
      if (svc) {
        await api.put(`/services/${svc.id}`, payload);
      } else {
        await api.post("/services/", payload);
      }
      onSave();
    } catch {
      notify("Failed to save service.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: "var(--surface)", borderRadius: 16, padding: 28,
        width: 420, boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
      }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 17 }}>{svc ? "Edit Service" : "Add Service"}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)" }}>
            <X size={20} />
          </button>
        </div>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Service Name *</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Hydra Facial, Laser Hair Removal"
              required
            />
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Duration (min)</label>
              <input
                className="input"
                type="number"
                min="5"
                value={form.duration_minutes}
                onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Price (PKR)</label>
              <input
                className="input"
                type="number"
                min="0"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                placeholder="optional"
              />
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Room Modal ────────────────────────────────────────────────────────────────
function RoomModal({ room, onClose, onSave }) {
  const [name, setName] = useState(room?.name || "");
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (room) {
        await api.put(`/rooms/${room.id}`, { name: name.trim() });
      } else {
        await api.post("/rooms/", { name: name.trim() });
      }
      onSave();
    } catch {
      notify("Failed to save room.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: "var(--surface)", borderRadius: 16, padding: 28,
        width: 360, boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
      }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 17 }}>{room ? "Edit Room" : "Add Room"}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)" }}>
            <X size={20} />
          </button>
        </div>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Room Name *</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Room 1, Treatment Room A"
              required
            />
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Services() {
  const [services, setServices] = useState(null);
  const [rooms, setRooms] = useState(null);
  const [loading, setLoading] = useState(true);
  const [svcModal, setSvcModal] = useState(null); // null | "new" | service object
  const [roomModal, setRoomModal] = useState(null);
  const { notify } = useToast();

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [sRes, rRes] = await Promise.all([api.get("/services/"), api.get("/rooms/")]);
      setServices(sRes.data);
      setRooms(rRes.data);
    } catch {
      notify("Failed to load services.", "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const deleteService = async (id) => {
    if (!window.confirm("Remove this service?")) return;
    try {
      await api.delete(`/services/${id}`);
      fetchAll();
    } catch {
      notify("Failed to remove service.", "error");
    }
  };

  const deleteRoom = async (id) => {
    if (!window.confirm("Remove this room?")) return;
    try {
      await api.delete(`/rooms/${id}`);
      fetchAll();
    } catch {
      notify("Failed to remove room.", "error");
    }
  };

  return (
    <AppLayout
      title="Services & Rooms"
      subtitle="Manage clinic services (treatments, procedures) and treatment rooms."
      actions={
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-secondary" onClick={() => setRoomModal("new")}>
            <Plus size={15} /> Add Room
          </button>
          <button className="btn btn-primary" onClick={() => setSvcModal("new")}>
            <Plus size={15} /> Add Service
          </button>
        </div>
      }
    >
      {loading ? (
        <SkeletonBlock className="skeleton-table" />
      ) : (
        <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>

          {/* Services */}
          <div style={{ flex: "2 1 400px" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700 }}>
              <Scissors size={15} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Services ({services?.length ?? 0})
            </h3>
            {services?.length === 0 ? (
              <div style={{
                background: "var(--surface)", border: "1px solid var(--line)",
                borderRadius: 12, padding: "40px 20px", textAlign: "center", color: "var(--muted)",
              }}>
                No services yet. Add the treatments your clinic offers.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {services.map((s) => (
                  <div key={s.id} style={{
                    background: "var(--surface)", border: "1px solid var(--line)",
                    borderRadius: 12, padding: "14px 18px",
                    display: "flex", alignItems: "center", gap: 12,
                  }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>{s.name}</p>
                      <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--muted)" }}>
                        {s.duration_minutes} min
                        {s.price != null ? ` · PKR ${Number(s.price).toLocaleString()}` : ""}
                      </p>
                    </div>
                    <button
                      onClick={() => setSvcModal(s)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", padding: 6 }}
                      title="Edit"
                    >
                      <Edit2 size={15} />
                    </button>
                    <button
                      onClick={() => deleteService(s.id)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#ef4444", padding: 6 }}
                      title="Remove"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Rooms */}
          <div style={{ flex: "1 1 260px" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700 }}>
              Rooms ({rooms?.length ?? 0})
            </h3>
            {rooms?.length === 0 ? (
              <div style={{
                background: "var(--surface)", border: "1px solid var(--line)",
                borderRadius: 12, padding: "40px 20px", textAlign: "center", color: "var(--muted)",
              }}>
                No rooms yet. Add treatment rooms.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {rooms.map((r) => (
                  <div key={r.id} style={{
                    background: "var(--surface)", border: "1px solid var(--line)",
                    borderRadius: 12, padding: "14px 18px",
                    display: "flex", alignItems: "center", gap: 12,
                  }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>{r.name}</p>
                      <p style={{ margin: "3px 0 0", fontSize: 12 }}>
                        <span style={{
                          color: r.is_occupied ? "#ef4444" : "#10b981",
                          fontWeight: 700,
                        }}>
                          {r.is_occupied ? "Occupied" : "Free"}
                        </span>
                      </p>
                    </div>
                    <button
                      onClick={() => setRoomModal(r)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", padding: 6 }}
                      title="Edit"
                    >
                      <Edit2 size={15} />
                    </button>
                    <button
                      onClick={() => deleteRoom(r.id)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#ef4444", padding: 6 }}
                      title="Remove"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {svcModal && (
        <ServiceModal
          svc={svcModal === "new" ? null : svcModal}
          onClose={() => setSvcModal(null)}
          onSave={() => { setSvcModal(null); fetchAll(); }}
        />
      )}
      {roomModal && (
        <RoomModal
          room={roomModal === "new" ? null : roomModal}
          onClose={() => setRoomModal(null)}
          onSave={() => { setRoomModal(null); fetchAll(); }}
        />
      )}
    </AppLayout>
  );
}
