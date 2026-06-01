import { Lock, X } from "lucide-react";
import { PLANS, UPGRADE_MESSAGE } from "../config/plans";
import { usePlan } from "../hooks/usePlan";

export default function UpgradeModal({ feature, onClose }) {
  const { plan } = usePlan();
  const info = UPGRADE_MESSAGE[feature];
  if (!info) return null;

  const targetPlan = PLANS[info.need.toLowerCase()];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card"
        style={{ maxWidth: 420, width: "90%" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%",
              background: "var(--accent-soft)", display: "flex",
              alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}>
              <Lock size={18} color="var(--accent)" />
            </div>
            <div>
              <h2 style={{ margin: 0 }}>Upgrade to {info.need}</h2>
              <p style={{ margin: 0 }}>{info.reason}</p>
            </div>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          <div style={{
            background: "var(--bg)", border: "1px solid var(--line)",
            borderRadius: 10, padding: "14px 16px", marginBottom: 20,
          }}>
            <p style={{ margin: "0 0 8px", fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Your plan upgrade
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className="badge" style={{ background: PLANS[plan]?.color || "#6b7280", color: "#fff" }}>
                {PLANS[plan]?.label || "Starter"}
              </span>
              <span style={{ fontSize: 13, color: "var(--muted)" }}>→</span>
              <span className="badge" style={{ background: targetPlan?.color || "#2563eb", color: "#fff" }}>
                {targetPlan?.label}
              </span>
            </div>
          </div>

          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>
            Contact us on WhatsApp to upgrade your plan. We'll activate it within a few hours.
          </p>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <a
            href="https://wa.me/923000000000?text=I want to upgrade my clinic plan"
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: "none", flex: 1, justifyContent: "center" }}
          >
            Contact us on WhatsApp
          </a>
          <button className="btn btn-secondary" onClick={onClose}>
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}
