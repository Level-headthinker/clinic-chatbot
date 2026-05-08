import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { DollarSign, TrendingUp, Clock, CheckCircle } from "lucide-react";

const STATUS_COLORS = {
  paid: { bg: "#dcfce7", color: "#16a34a" },
  unpaid: { bg: "#fee2e2", color: "#dc2626" },
  partial: { bg: "#fef9c3", color: "#ca8a04" },
  waived: { bg: "#f1f5f9", color: "#64748b" },
};

export default function Billing() {
  const [invoices, setInvoices] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [chargeForm, setChargeForm] = useState({ description: "", amount: "" });
  const [showChargeId, setShowChargeId] = useState(null);

  useEffect(() => {
    fetchData();
  }, [filter]);

  const fetchData = async () => {
    try {
      const [invRes, statsRes] = await Promise.all([
        api.get(filter ? `/billing/?payment_status=${filter}` : "/billing/"),
        api.get("/billing/stats")
      ]);
      setInvoices(invRes.data);
      setStats(statsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const updatePayment = async (id, paid_amount, payment_method) => {
    try {
      await api.put(`/billing/${id}/payment`, {
        paid_amount: parseInt(paid_amount),
        payment_method
      });
      fetchData();
    } catch (err) {
      alert("Failed to update payment");
    }
  };

  const markPaid = async (invoice) => {
    await updatePayment(
      invoice.id,
      invoice.total_amount,
      "cash"
    );
  };

  const addCharge = async (invoiceId) => {
    if (!chargeForm.description || !chargeForm.amount) return;
    try {
      await api.post(`/billing/${invoiceId}/charges`, {
        description: chargeForm.description,
        amount: parseInt(chargeForm.amount)
      });
      setChargeForm({ description: "", amount: "" });
      setShowChargeId(null);
      fetchData();
    } catch (err) {
      alert("Failed to add charge");
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <div style={styles.topBar}>
          <h1 style={styles.heading}>Billing</h1>
          <select
            style={styles.select}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">All Invoices</option>
            <option value="paid">Paid</option>
            <option value="unpaid">Unpaid</option>
            <option value="partial">Partial</option>
          </select>
        </div>

        {/* Stats */}
        {stats && (
          <div style={styles.statsGrid}>
            <div style={{ ...styles.statCard, backgroundColor: "#f0fdf4" }}>
              <div style={styles.statIcon}>
                <TrendingUp size={22} color="#16a34a" />
              </div>
              <div>
                <p style={styles.statLabel}>Total Revenue</p>
                <p style={styles.statValue}>
                  PKR {stats.total_revenue.toLocaleString()}
                </p>
              </div>
            </div>
            <div style={{ ...styles.statCard, backgroundColor: "#fffbeb" }}>
              <div style={styles.statIcon}>
                <Clock size={22} color="#ca8a04" />
              </div>
              <div>
                <p style={styles.statLabel}>Pending Amount</p>
                <p style={styles.statValue}>
                  PKR {stats.pending_amount.toLocaleString()}
                </p>
              </div>
            </div>
            <div style={{ ...styles.statCard, backgroundColor: "#eff6ff" }}>
              <div style={styles.statIcon}>
                <DollarSign size={22} color="#2563eb" />
              </div>
              <div>
                <p style={styles.statLabel}>Today's Revenue</p>
                <p style={styles.statValue}>
                  PKR {stats.today_revenue.toLocaleString()}
                </p>
              </div>
            </div>
            <div style={{ ...styles.statCard, backgroundColor: "#f5f3ff" }}>
              <div style={styles.statIcon}>
                <CheckCircle size={22} color="#7c3aed" />
              </div>
              <div>
                <p style={styles.statLabel}>Collection Rate</p>
                <p style={styles.statValue}>{stats.collection_rate}</p>
              </div>
            </div>
          </div>
        )}

        {/* Revenue summary bar */}
        {stats && (
          <div style={styles.summaryBar}>
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Total Invoices</span>
              <span style={styles.summaryValue}>{stats.total_invoices}</span>
            </div>
            <div style={styles.summaryDivider} />
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Paid</span>
              <span style={{ ...styles.summaryValue, color: "#16a34a" }}>
                {stats.paid_invoices}
              </span>
            </div>
            <div style={styles.summaryDivider} />
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Unpaid</span>
              <span style={{ ...styles.summaryValue, color: "#dc2626" }}>
                {stats.unpaid_invoices}
              </span>
            </div>
            <div style={styles.summaryDivider} />
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Today's Invoices</span>
              <span style={styles.summaryValue}>{stats.today_invoices}</span>
            </div>
          </div>
        )}

        {/* Invoices table */}
        <div style={styles.tableCard}>
          {loading ? (
            <p>Loading...</p>
          ) : invoices.length === 0 ? (
            <p style={styles.empty}>
              No invoices yet. Invoices are created automatically when you record a visit with a fee.
            </p>
          ) : (
            invoices.map((inv) => (
              <div key={inv.id} style={styles.invoiceItem}>
                <div style={styles.invoiceRow}>
                  <div style={styles.invoiceLeft}>
                    <p style={styles.invoiceNumber}>{inv.invoice_number}</p>
                    <p style={styles.invoicePatient}>
                      {inv.patient_name} · {inv.patient_phone}
                    </p>
                    <p style={styles.invoiceDate}>
                      {new Date(inv.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <div style={styles.invoiceMiddle}>
                    <p style={styles.invoiceFee}>
                      Consultation: PKR {inv.consultation_fee.toLocaleString()}
                    </p>
                    {inv.additional_charges && inv.additional_charges.length > 0 && (
                      <p style={styles.invoiceExtra}>
                        + {inv.additional_charges.length} extra charge(s)
                      </p>
                    )}
                    <p style={styles.invoiceTotal}>
                      Total: PKR {inv.total_amount.toLocaleString()}
                    </p>
                    {inv.balance > 0 && (
                      <p style={styles.invoiceBalance}>
                        Balance: PKR {inv.balance.toLocaleString()}
                      </p>
                    )}
                  </div>

                  <div style={styles.invoiceRight}>
                    <span style={{
                      ...styles.statusBadge,
                      backgroundColor: STATUS_COLORS[inv.payment_status]?.bg || "#f1f5f9",
                      color: STATUS_COLORS[inv.payment_status]?.color || "#64748b"
                    }}>
                      {inv.payment_status.toUpperCase()}
                    </span>

                    <div style={styles.actionBtns}>
                      {inv.payment_status !== "paid" && (
                        <button
                          onClick={() => markPaid(inv)}
                          style={styles.paidBtn}
                        >
                          ✅ Mark Paid
                        </button>
                      )}
                      <button
                        onClick={() => setExpandedId(
                          expandedId === inv.id ? null : inv.id
                        )}
                        style={styles.expandBtn}
                      >
                        {expandedId === inv.id ? "▲ Less" : "▼ More"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded section */}
                {expandedId === inv.id && (
                  <div style={styles.expandedSection}>

                    {inv.additional_charges && inv.additional_charges.length > 0 && (
                      <div style={styles.chargesBox}>
                        <p style={styles.expandLabel}>Additional Charges</p>
                        {inv.additional_charges.map((c, i) => (
                          <div key={i} style={styles.chargeRow}>
                            <span>{c.description}</span>
                            <span>PKR {c.amount.toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add charge */}
                    {showChargeId === inv.id ? (
                      <div style={styles.addChargeForm}>
                        <input
                          style={{ ...styles.smallInput, flex: 2 }}
                          placeholder="Description (e.g. Lab test)"
                          value={chargeForm.description}
                          onChange={(e) => setChargeForm({
                            ...chargeForm, description: e.target.value
                          })}
                        />
                        <input
                          style={{ ...styles.smallInput, flex: 1 }}
                          placeholder="Amount (PKR)"
                          type="number"
                          value={chargeForm.amount}
                          onChange={(e) => setChargeForm({
                            ...chargeForm, amount: e.target.value
                          })}
                        />
                        <button
                          onClick={() => addCharge(inv.id)}
                          style={styles.paidBtn}
                        >
                          Add
                        </button>
                        <button
                          onClick={() => setShowChargeId(null)}
                          style={styles.expandBtn}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowChargeId(inv.id)}
                        style={styles.addChargeBtn}
                      >
                        + Add Extra Charge
                      </button>
                    )}

                    {/* Partial payment */}
                    {inv.payment_status !== "paid" && (
                      <div style={styles.partialForm}>
                        <p style={styles.expandLabel}>Record Partial Payment</p>
                        <div style={styles.addChargeForm}>
                          <input
                            style={{ ...styles.smallInput, flex: 1 }}
                            placeholder="Amount paid (PKR)"
                            type="number"
                            id={`paid-${inv.id}`}
                          />
                          <select
                            style={{ ...styles.smallInput, flex: 1 }}
                            id={`method-${inv.id}`}
                          >
                            <option value="cash">Cash</option>
                            <option value="jazzcash">JazzCash</option>
                            <option value="easypaisa">EasyPaisa</option>
                            <option value="card">Card</option>
                            <option value="bank">Bank Transfer</option>
                          </select>
                          <button
                            onClick={() => {
                              const amount = document.getElementById(`paid-${inv.id}`).value;
                              const method = document.getElementById(`method-${inv.id}`).value;
                              if (amount) updatePayment(inv.id, amount, method);
                            }}
                            style={styles.paidBtn}
                          >
                            Save Payment
                          </button>
                        </div>
                      </div>
                    )}

                    {inv.notes && (
                      <p style={styles.invoiceNotes}>📝 {inv.notes}</p>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  layout: { display: "flex", minHeight: "100vh", backgroundColor: "#f8fafc" },
  main: { marginLeft: "240px", padding: "32px", flex: 1 },
  topBar: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: "24px"
  },
  heading: { fontSize: "24px", fontWeight: "700", color: "#1e293b", margin: 0 },
  select: {
    padding: "10px 12px", borderRadius: "8px",
    border: "1px solid #d1d5db", fontSize: "14px",
    outline: "none", cursor: "pointer"
  },
  statsGrid: {
    display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
    gap: "16px", marginBottom: "16px"
  },
  statCard: {
    borderRadius: "12px", padding: "18px 20px",
    display: "flex", alignItems: "center", gap: "14px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  statIcon: { padding: "10px", borderRadius: "10px", backgroundColor: "#fff" },
  statLabel: { fontSize: "12px", color: "#6b7280", margin: "0 0 3px 0" },
  statValue: { fontSize: "20px", fontWeight: "700", color: "#1e293b", margin: 0 },
  summaryBar: {
    backgroundColor: "#1e3a5f", borderRadius: "12px",
    padding: "16px 28px", marginBottom: "24px",
    display: "flex", gap: "0", alignItems: "center"
  },
  summaryItem: {
    display: "flex", flexDirection: "column",
    alignItems: "center", flex: 1
  },
  summaryLabel: { fontSize: "11px", color: "#93c5fd", textTransform: "uppercase" },
  summaryValue: { fontSize: "20px", fontWeight: "700", color: "#fff" },
  summaryDivider: { width: "1px", height: "36px", backgroundColor: "#2d5a8e" },
  tableCard: {
    backgroundColor: "#fff", borderRadius: "12px",
    padding: "8px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
  },
  empty: { color: "#9ca3af", fontSize: "14px", padding: "20px" },
  invoiceItem: {
    borderBottom: "1px solid #f1f5f9", padding: "16px"
  },
  invoiceRow: {
    display: "flex", justifyContent: "space-between",
    alignItems: "flex-start", gap: "16px"
  },
  invoiceLeft: { flex: 1 },
  invoiceNumber: {
    fontSize: "13px", fontWeight: "700",
    color: "#2563eb", margin: "0 0 3px 0"
  },
  invoicePatient: {
    fontSize: "14px", fontWeight: "600",
    color: "#1e293b", margin: "0 0 3px 0"
  },
  invoiceDate: { fontSize: "12px", color: "#94a3b8", margin: 0 },
  invoiceMiddle: { flex: 1 },
  invoiceFee: { fontSize: "13px", color: "#374151", margin: "0 0 2px 0" },
  invoiceExtra: { fontSize: "12px", color: "#94a3b8", margin: "0 0 2px 0" },
  invoiceTotal: {
    fontSize: "15px", fontWeight: "700",
    color: "#1e293b", margin: "0 0 2px 0"
  },
  invoiceBalance: { fontSize: "13px", color: "#dc2626", margin: 0, fontWeight: "600" },
  invoiceRight: {
    display: "flex", flexDirection: "column",
    alignItems: "flex-end", gap: "8px"
  },
  statusBadge: {
    padding: "4px 12px", borderRadius: "20px",
    fontSize: "11px", fontWeight: "700"
  },
  actionBtns: { display: "flex", gap: "6px" },
  paidBtn: {
    backgroundColor: "#dcfce7", color: "#16a34a",
    border: "none", padding: "6px 12px",
    borderRadius: "6px", cursor: "pointer",
    fontWeight: "600", fontSize: "12px"
  },
  expandBtn: {
    backgroundColor: "#f1f5f9", color: "#374151",
    border: "none", padding: "6px 12px",
    borderRadius: "6px", cursor: "pointer",
    fontWeight: "600", fontSize: "12px"
  },
  expandedSection: {
    marginTop: "14px", paddingTop: "14px",
    borderTop: "1px solid #f1f5f9",
    display: "flex", flexDirection: "column", gap: "10px"
  },
  expandLabel: {
    fontSize: "11px", color: "#94a3b8",
    textTransform: "uppercase", margin: "0 0 6px 0", fontWeight: "600"
  },
  chargesBox: {
    backgroundColor: "#f8fafc", borderRadius: "8px", padding: "12px"
  },
  chargeRow: {
    display: "flex", justifyContent: "space-between",
    fontSize: "13px", color: "#374151",
    padding: "3px 0"
  },
  addChargeBtn: {
    backgroundColor: "#eff6ff", color: "#2563eb",
    border: "1px solid #bfdbfe", padding: "7px 14px",
    borderRadius: "8px", cursor: "pointer",
    fontWeight: "600", fontSize: "13px",
    alignSelf: "flex-start"
  },
  addChargeForm: { display: "flex", gap: "8px", alignItems: "center" },
  smallInput: {
    padding: "8px 10px", borderRadius: "6px",
    border: "1px solid #d1d5db", fontSize: "13px", outline: "none"
  },
  partialForm: {},
  invoiceNotes: { fontSize: "13px", color: "#64748b" },
};