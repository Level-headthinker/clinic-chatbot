import { useCallback, useEffect, useState } from "react";
import { CheckCircle, Clock, DollarSign, Download, Plus, TrendingUp } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

export default function Billing() {
  const [invoices, setInvoices] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [chargeForm, setChargeForm] = useState({ description: "", amount: "" });
  const [showChargeId, setShowChargeId] = useState(null);
  const { notify } = useToast();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [invRes, statsRes] = await Promise.all([
        api.get(filter ? `/billing/?payment_status=${filter}` : "/billing/"),
        api.get("/billing/stats"),
      ]);
      setInvoices(invRes.data);
      setStats(statsRes.data);
    } catch {
      notify("Failed to load billing data.", "error");
    } finally {
      setLoading(false);
    }
  }, [filter, notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updatePayment = async (id, paidAmount, paymentMethod) => {
    try {
      await api.put(`/billing/${id}/payment`, {
        paid_amount: parseInt(paidAmount),
        payment_method: paymentMethod,
      });
      notify("Payment updated.", "success");
      fetchData();
    } catch {
      notify("Failed to update payment.", "error");
    }
  };

  const addCharge = async (invoiceId) => {
    if (!chargeForm.description || !chargeForm.amount) return;
    try {
      await api.post(`/billing/${invoiceId}/charges`, {
        description: chargeForm.description,
        amount: parseInt(chargeForm.amount),
      });
      setChargeForm({ description: "", amount: "" });
      setShowChargeId(null);
      notify("Charge added.", "success");
      fetchData();
    } catch {
      notify("Failed to add charge.", "error");
    }
  };

  return (
    <AppLayout
      title="Billing"
      subtitle="Track invoices, collections, balances, and extra charges."
      actions={
        <select className="select" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All invoices</option>
          <option value="paid">Paid</option>
          <option value="unpaid">Unpaid</option>
          <option value="partial">Partial</option>
        </select>
      }
    >
      {stats && (
        <div className="metric-grid">
          <Metric icon={<TrendingUp size={22} />} label="Total revenue" value={`PKR ${stats.total_revenue.toLocaleString()}`} />
          <Metric icon={<Clock size={22} />} label="Pending" value={`PKR ${stats.pending_amount.toLocaleString()}`} />
          <Metric icon={<DollarSign size={22} />} label="Today" value={`PKR ${stats.today_revenue.toLocaleString()}`} />
          <Metric icon={<CheckCircle size={22} />} label="Collection" value={stats.collection_rate} />
        </div>
      )}

      <section className="table-panel">
        <div className="panel-header">
          <h2>Invoices</h2>
          {stats && <span className="badge">{stats.total_invoices} total</span>}
        </div>

        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : invoices.length === 0 ? (
          <EmptyState
            title="No invoices yet"
            description="Invoices are created automatically when a visit is recorded with a consultation fee."
          />
        ) : (
          <div className="invoice-list" style={{ padding: 12 }}>
            {invoices.map((invoice) => (
              <article className="invoice-card" key={invoice.id}>
                <div className="invoice-top">
                  <div>
                    <p className="invoice-number">{invoice.invoice_number}</p>
                    <strong>{invoice.patient_name}</strong>
                    <p className="muted" style={{ margin: "4px 0 0" }}>{invoice.patient_phone}</p>
                  </div>
                  <div>
                    <p className="record-label">Total</p>
                    <p className="record-value">PKR {invoice.total_amount.toLocaleString()}</p>
                    {invoice.balance > 0 && <p className="muted">Balance PKR {invoice.balance.toLocaleString()}</p>}
                  </div>
                  <div className="action-row" style={{ justifyContent: "flex-end" }}>
                    <span className={`badge ${paymentBadge(invoice.payment_status)}`}>{invoice.payment_status}</span>
                    <button className="icon-btn" title="Print invoice" onClick={() => window.print()}><Download size={16} /></button>
                  </div>
                </div>

                <div className="action-row">
                  {invoice.payment_status !== "paid" && (
                    <button className="btn btn-primary" onClick={() => updatePayment(invoice.id, invoice.total_amount, "cash")}>
                      Mark paid
                    </button>
                  )}
                  <button className="btn btn-secondary" onClick={() => setExpandedId(expandedId === invoice.id ? null : invoice.id)}>
                    {expandedId === invoice.id ? "Hide details" : "Details"}
                  </button>
                  <button className="btn btn-secondary" onClick={() => setShowChargeId(showChargeId === invoice.id ? null : invoice.id)}>
                    <Plus size={16} />
                    Add charge
                  </button>
                </div>

                {showChargeId === invoice.id && (
                  <div className="action-row">
                    <input className="input" placeholder="Description" value={chargeForm.description} onChange={(e) => setChargeForm({ ...chargeForm, description: e.target.value })} />
                    <input className="input" type="number" placeholder="Amount" value={chargeForm.amount} onChange={(e) => setChargeForm({ ...chargeForm, amount: e.target.value })} />
                    <button className="btn btn-primary" onClick={() => addCharge(invoice.id)}>Save charge</button>
                  </div>
                )}

                {expandedId === invoice.id && (
                  <div className="record-grid">
                    <Info label="Consultation" value={`PKR ${invoice.consultation_fee.toLocaleString()}`} />
                    <Info label="Paid" value={`PKR ${invoice.paid_amount.toLocaleString()}`} />
                    <Info label="Method" value={invoice.payment_method || "-"} />
                    <Info label="Created" value={new Date(invoice.created_at).toLocaleDateString()} />
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </AppLayout>
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

function Info({ label, value }) {
  return (
    <div className="record-card">
      <p className="record-label">{label}</p>
      <p className="record-value" style={{ fontSize: 16 }}>{value}</p>
    </div>
  );
}

function paymentBadge(status) {
  if (status === "paid") return "badge-success";
  if (status === "partial") return "badge-warning";
  return "badge-danger";
}
