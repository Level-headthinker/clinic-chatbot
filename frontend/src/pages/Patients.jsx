import { useCallback, useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import EmptyState from "../components/EmptyState";
import { SkeletonBlock } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";

const emptyForm = {
  name: "",
  phone: "",
  age: "",
  gender: "",
  blood_group: "",
  allergies: "",
  chronic_conditions: "",
  emergency_contact: "",
};

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const navigate = useNavigate();
  const { notify } = useToast();

  const fetchPatients = useCallback(async () => {
    setLoading(true);
    try {
      const url = search ? `/patients/?search=${encodeURIComponent(search)}` : "/patients/";
      const res = await api.get(url);
      setPatients(res.data);
    } catch {
      notify("Failed to load patients.", "error");
    } finally {
      setLoading(false);
    }
  }, [search, notify]);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const savePatient = async (event) => {
    event.preventDefault();
    try {
      await api.post("/patients/", {
        ...form,
        age: form.age ? parseInt(form.age) : null,
      });
      setForm(emptyForm);
      setShowForm(false);
      notify("Patient added.", "success");
      fetchPatients();
    } catch (err) {
      notify(err.response?.data?.detail || "Failed to add patient.", "error");
    }
  };

  return (
    <AppLayout
      title="Patients"
      subtitle="Search records, review histories, and create new patient profiles."
      actions={
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} />
          {showForm ? "Close form" : "Add patient"}
        </button>
      }
    >
      {showForm && (
        <section className="form-panel">
          <h2>Add new patient</h2>
          <form onSubmit={savePatient} className="form-stack">
            <div className="form-grid">
              <input className="input" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <input className="input" placeholder="Phone number" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
              <input className="input" placeholder="Age" type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} />
              <select className="select" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="">Select gender</option>
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
              </select>
              <select className="select" value={form.blood_group} onChange={(e) => setForm({ ...form, blood_group: e.target.value })}>
                <option value="">Blood group</option>
                {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((group) => <option key={group}>{group}</option>)}
              </select>
              <input className="input" placeholder="Emergency contact" value={form.emergency_contact} onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })} />
            </div>
            <input className="input" placeholder="Allergies" value={form.allergies} onChange={(e) => setForm({ ...form, allergies: e.target.value })} />
            <input className="input" placeholder="Chronic conditions" value={form.chronic_conditions} onChange={(e) => setForm({ ...form, chronic_conditions: e.target.value })} />
            <div className="action-row">
              <button className="btn btn-primary" type="submit">Save patient</button>
              <button className="btn btn-secondary" type="button" onClick={() => { setForm(emptyForm); setShowForm(false); }}>Cancel</button>
            </div>
          </form>
        </section>
      )}

      <div className="toolbar">
        <div className="search-box">
          <Search size={16} />
          <input placeholder="Search by name or phone..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <section className="table-panel">
        <div className="panel-header">
          <h2>Patient records</h2>
          <span className="badge">{patients.length} visible</span>
        </div>
        {loading ? (
          <SkeletonBlock className="skeleton-table" />
        ) : patients.length === 0 ? (
          <EmptyState
            title="No patients found"
            description="Create your first patient profile or import existing records from the Leads page."
            action={<button className="btn btn-primary" onClick={() => setShowForm(true)}>Add patient</button>}
          />
        ) : (
          <table className="responsive-table">
            <thead>
              <tr>{["Name", "Phone", "Age", "Gender", "Blood Group", "Conditions", "Visits", "Action"].map((h) => <th key={h}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {patients.map((patient) => (
                <tr key={patient.id}>
                  <td data-label="Name">
                    <div className="profile-left">
                      <span className="avatar-sm">{patient.name.charAt(0).toUpperCase()}</span>
                      <strong>{patient.name}</strong>
                    </div>
                  </td>
                  <td data-label="Phone">{patient.phone}</td>
                  <td data-label="Age">{patient.age || "-"}</td>
                  <td data-label="Gender">{patient.gender || "-"}</td>
                  <td data-label="Blood Group">{patient.blood_group ? <span className="badge badge-danger">{patient.blood_group}</span> : "-"}</td>
                  <td data-label="Conditions">{patient.chronic_conditions ? `${patient.chronic_conditions.slice(0, 34)}...` : "-"}</td>
                  <td data-label="Visits"><span className="badge">{patient.total_visits} visits</span></td>
                  <td data-label="Action">
                    <button className="btn btn-secondary" onClick={() => navigate(`/patients/${patient.id}`)}>View record</button>
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
