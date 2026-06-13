import { useMemo, useState } from "react";
import {
  Upload,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Download,
  Wand2,
} from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useToast } from "../context/ToastContext";

const ENTITIES = [
  { value: "patients", label: "Patients" },
  { value: "doctors", label: "Doctors" },
  { value: "staff", label: "Staff" },
  { value: "services", label: "Services" },
  { value: "appointments", label: "Appointments" },
];

const SKIP = "__skip__";

// FormData upload — override the axios instance's default JSON content-type.
function postForm(url, formData) {
  return api.post(url, formData, { headers: { "Content-Type": "multipart/form-data" } });
}

function downloadBase64Csv(b64, filename) {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  const url = window.URL.createObjectURL(new Blob([arr], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export default function DataImport() {
  const [entity, setEntity] = useState("patients");
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState({}); // { header: field | SKIP }
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const { notify } = useToast();

  const reset = (toEntity = entity) => {
    setEntity(toEntity);
    setStep(1);
    setFile(null);
    setPreview(null);
    setMapping({});
    setResult(null);
  };

  // ── Step 1 → 2: upload & preview ───────────────────────────
  const runPreview = async () => {
    if (!file) {
      notify("Choose a CSV or Excel file first.", "error");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await postForm(`/import/${entity}/preview`, fd);
      setPreview(res.data);
      // Seed the mapping from the server's fuzzy pre-fill (skip = unmapped).
      const seeded = {};
      res.data.headers.forEach((h) => {
        seeded[h] = res.data.prefill_mapping?.[h] || SKIP;
      });
      setMapping(seeded);
      setStep(2);
    } catch (e) {
      notify(e.response?.data?.detail || "Could not read that file.", "error");
    } finally {
      setBusy(false);
    }
  };

  // ── Required-field gate for step 2 ─────────────────────────
  const mappedFields = useMemo(
    () => new Set(Object.values(mapping).filter((v) => v && v !== SKIP)),
    [mapping]
  );
  const missingRequired = useMemo(
    () => (preview?.required_fields || []).filter((f) => !mappedFields.has(f)),
    [preview, mappedFields]
  );
  const fieldLabel = (f) => preview?.fields?.find((x) => x.field === f)?.label || f;

  const buildMappingPayload = () => {
    const out = {};
    Object.entries(mapping).forEach(([header, field]) => {
      if (field && field !== SKIP) out[header] = field;
    });
    return JSON.stringify(out);
  };

  // ── Step 2 → 3: validate (dry run) or import ───────────────
  const runCommit = async (dryRun) => {
    if (missingRequired.length > 0) {
      notify(`Map the required field(s): ${missingRequired.map(fieldLabel).join(", ")}`, "error");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("mapping", buildMappingPayload());
      fd.append("dry_run", dryRun ? "true" : "false");
      const res = await postForm(`/import/${entity}/commit`, fd);
      setResult({ ...res.data, was_dry_run: dryRun });
      if (!dryRun) {
        setStep(3);
        notify(`Imported ${res.data.created} record(s).`, "success");
      } else {
        notify(`Validation done — ${res.data.valid_rows} valid, ${res.data.failed_rows} with errors.`, "info");
      }
    } catch (e) {
      notify(e.response?.data?.detail || "Import failed.", "error");
    } finally {
      setBusy(false);
    }
  };

  const onPickField = (header, value) =>
    setMapping((m) => ({ ...m, [header]: value }));

  return (
    <AppLayout
      title="Import Data"
      subtitle="Bring in patients, doctors, staff, services or appointments from a spreadsheet."
      actions={
        <select
          className="select"
          value={entity}
          onChange={(e) => reset(e.target.value)}
          disabled={step !== 1}
          title={step !== 1 ? "Start over to change the import type" : "What to import"}
        >
          {ENTITIES.map((x) => (
            <option key={x.value} value={x.value}>{x.label}</option>
          ))}
        </select>
      }
    >
      <Stepper step={step} />

      {/* ── STEP 1 — upload ─────────────────────────────────── */}
      {step === 1 && (
        <section className="table-panel">
          <div className="panel-header"><h2>1. Upload your file</h2></div>
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16, maxWidth: 560 }}>
            <p className="muted" style={{ margin: 0 }}>
              Accepted: <strong>.csv</strong> or <strong>.xlsx</strong> (max 5 MB, 2000 rows).
              The first row must be column headers. Nothing is saved until you confirm in step 3.
            </p>
            <label className="upload-drop" style={uploadDropStyle}>
              <Upload size={26} color="var(--accent, #0d9488)" />
              <span style={{ fontWeight: 600 }}>
                {file ? file.name : "Click to choose a CSV or Excel file"}
              </span>
              {file && <span className="muted" style={{ fontSize: 12 }}>{(file.size / 1024).toFixed(0)} KB</span>}
              <input
                type="file"
                accept=".csv,.xlsx,.txt"
                style={{ display: "none" }}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <div className="action-row">
              <button className="btn btn-primary" onClick={runPreview} disabled={!file || busy}>
                {busy ? "Reading…" : <>Preview & map <ArrowRight size={16} /></>}
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ── STEP 2 — column mapping ─────────────────────────── */}
      {step === 2 && preview && (
        <>
          <section className="table-panel">
            <div className="panel-header">
              <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Wand2 size={18} /> 2. Match your columns
              </h2>
              <span className="badge">{preview.total_data_rows} rows</span>
            </div>
            <p className="muted" style={{ padding: "0 16px", marginTop: -4 }}>
              We auto-matched columns where we were confident. Review each one — pick a field or
              choose “Skip”. Required fields are marked <span style={{ color: "#ef4444" }}>*</span>.
            </p>
            <div style={{ overflowX: "auto", padding: 12 }}>
              <table className="data-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>Your column</th>
                    <th>Sample value</th>
                    <th>Maps to</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.headers.map((header, idx) => {
                    const suggestion = preview.suggestions?.[header];
                    const sample = preview.sample_rows?.[0]?.[idx] ?? "";
                    return (
                      <tr key={header}>
                        <td><strong>{header}</strong></td>
                        <td className="muted" style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {String(sample) || "—"}
                        </td>
                        <td>
                          <select
                            className="select"
                            value={mapping[header] || SKIP}
                            onChange={(e) => onPickField(header, e.target.value)}
                          >
                            <option value={SKIP}>— Skip this field —</option>
                            {preview.fields.map((f) => (
                              <option key={f.field} value={f.field}>
                                {f.label}{f.required ? " *" : ""}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td><ConfidenceBadge suggestion={suggestion} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {missingRequired.length > 0 && (
              <div style={warnBoxStyle}>
                <AlertTriangle size={16} />
                <span>
                  Map these required field(s) to continue:{" "}
                  <strong>{missingRequired.map(fieldLabel).join(", ")}</strong>
                </span>
              </div>
            )}

            <div className="action-row" style={{ padding: 16 }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                <ArrowLeft size={16} /> Back
              </button>
              <button className="btn btn-secondary" onClick={() => runCommit(true)} disabled={busy || missingRequired.length > 0}>
                Validate rows
              </button>
              <button className="btn btn-primary" onClick={() => runCommit(false)} disabled={busy || missingRequired.length > 0}>
                {busy ? "Working…" : <>Import valid rows <ArrowRight size={16} /></>}
              </button>
            </div>
          </section>

          {/* dry-run validation report shown inline on step 2 */}
          {result?.was_dry_run && <ValidationReport result={result} entity={entity} />}
        </>
      )}

      {/* ── STEP 3 — done ───────────────────────────────────── */}
      {step === 3 && result && (
        <section className="table-panel">
          <div className="panel-header">
            <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={18} color="#16a34a" /> 3. Import complete
            </h2>
          </div>
          <div className="metric-grid" style={{ padding: 12 }}>
            <Metric label="Imported" value={result.created ?? 0} good />
            <Metric label="Skipped (duplicates)" value={result.skipped_duplicates ?? 0} />
            <Metric label="Rows with errors" value={result.failed_rows ?? 0} bad={result.failed_rows > 0} />
            <Metric label="Total rows" value={result.total_rows ?? 0} />
          </div>

          {result.notes && result.notes.length > 0 && (
            <div style={{ padding: "0 16px 12px" }}>
              <h3 style={{ margin: "8px 0" }}>Notes</h3>
              <ul style={{ margin: 0, paddingLeft: 18, color: "var(--muted)", fontSize: 13 }}>
                {result.notes.map((n, i) => (
                  <li key={i} style={{ marginBottom: 4 }}>{n.info || (n.errors || []).join("; ")}</li>
                ))}
              </ul>
            </div>
          )}

          {result.failed_rows > 0 && result.failed_rows_csv_base64 && (
            <div style={{ padding: "0 16px 12px" }}>
              <button
                className="btn btn-secondary"
                onClick={() => downloadBase64Csv(result.failed_rows_csv_base64, `failed_${entity}.csv`)}
              >
                <Download size={16} /> Download failed rows to fix & re-import
              </button>
            </div>
          )}

          <ErrorList errors={result.errors} />

          <div className="action-row" style={{ padding: 16 }}>
            <button className="btn btn-primary" onClick={() => reset()}>Import another file</button>
          </div>
        </section>
      )}
    </AppLayout>
  );
}

function Stepper({ step }) {
  const steps = ["Upload", "Map columns", "Done"];
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
      {steps.map((label, i) => {
        const n = i + 1;
        const active = n === step;
        const done = n < step;
        return (
          <div key={label} style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "6px 14px", borderRadius: 999,
            background: active ? "var(--accent, #0d9488)" : done ? "var(--surface-2)" : "var(--surface-2)",
            color: active ? "#fff" : "var(--muted)",
            fontSize: 13, fontWeight: 600,
            border: "1px solid var(--line)",
          }}>
            <span style={{
              width: 20, height: 20, borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              background: active ? "rgba(255,255,255,.25)" : "var(--surface)",
              fontSize: 12,
            }}>{done ? "✓" : n}</span>
            {label}
          </div>
        );
      })}
    </div>
  );
}

function ConfidenceBadge({ suggestion }) {
  if (!suggestion || !suggestion.field) return <span className="muted" style={{ fontSize: 12 }}>—</span>;
  const c = suggestion.confidence;
  const color = suggestion.auto ? "#16a34a" : c >= 50 ? "#d97706" : "#94a3b8";
  return (
    <span style={{ fontSize: 12, fontWeight: 700, color }}>
      {Math.round(c)}%{suggestion.auto ? "" : " (check)"}
    </span>
  );
}

function ValidationReport({ result, entity }) {
  return (
    <section className="table-panel" style={{ marginTop: 16 }}>
      <div className="panel-header">
        <h2>Validation result</h2>
        <span className={`badge ${result.failed_rows > 0 ? "badge-warning" : "badge-success"}`}>
          {result.valid_rows} valid / {result.failed_rows} errors
        </span>
      </div>
      {result.failed_rows > 0 && result.failed_rows_csv_base64 && (
        <div style={{ padding: "0 16px 8px" }}>
          <button
            className="btn btn-secondary"
            onClick={() => downloadBase64Csv(result.failed_rows_csv_base64, `failed_${entity}.csv`)}
          >
            <Download size={16} /> Download failed rows
          </button>
        </div>
      )}
      <ErrorList errors={result.errors} />
    </section>
  );
}

function ErrorList({ errors }) {
  if (!errors || errors.length === 0) return null;
  return (
    <div style={{ padding: 12 }}>
      <div style={{ overflowX: "auto" }}>
        <table className="data-table" style={{ width: "100%" }}>
          <thead><tr><th style={{ width: 70 }}>Row</th><th>What's wrong</th></tr></thead>
          <tbody>
            {errors.map((e, i) => (
              <tr key={i}>
                <td><strong>{e.row ?? "—"}</strong></td>
                <td style={{ color: "#ef4444", fontSize: 13 }}>
                  {(e.errors || []).join("; ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ label, value, good, bad }) {
  return (
    <div className="metric-card">
      <div>
        <p className="metric-label">{label}</p>
        <p className="metric-value" style={{ color: good ? "#16a34a" : bad ? "#ef4444" : undefined }}>
          {value}
        </p>
      </div>
    </div>
  );
}

const uploadDropStyle = {
  display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
  padding: "32px 20px", border: "2px dashed var(--line)", borderRadius: 12,
  cursor: "pointer", textAlign: "center", background: "var(--surface-2)",
};

const warnBoxStyle = {
  display: "flex", alignItems: "center", gap: 8,
  margin: "0 16px", padding: "10px 14px", borderRadius: 8,
  background: "rgba(239,68,68,.08)", color: "#ef4444", fontSize: 13,
};
