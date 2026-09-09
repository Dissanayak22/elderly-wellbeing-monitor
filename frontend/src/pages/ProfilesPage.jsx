import { useEffect, useState } from "react";
import { createElderly, listElderly } from "../services/api";

export default function ProfilesPage() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ elderly_code: "", full_name: "", age: "", notes: "" });
  const [error, setError] = useState("");

  async function refresh() {
    setRows(await listElderly());
  }

  useEffect(() => {
    refresh().catch(() => setError("Failed to load profiles."));
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await createElderly({
        elderly_code: form.elderly_code,
        full_name: form.full_name,
        age: form.age ? Number(form.age) : null,
        notes: form.notes || null,
      });
      setForm({ elderly_code: "", full_name: "", age: "", notes: "" });
      await refresh();
    } catch {
      setError("Could not create profile (code may already exist).");
    }
  }

  return (
    <div>
      <h1 className="page-title">Elderly profiles</h1>
      <p className="page-sub">Basic non-sensitive demo information for monitoring sessions.</p>

      <div className="panel card">
        <h2>Add profile</h2>
        <form onSubmit={onSubmit}>
          <div className="form-row">
            <label>Elderly ID</label>
            <input
              value={form.elderly_code}
              onChange={(e) => setForm({ ...form, elderly_code: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <label>Name</label>
            <input
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <label>Age</label>
            <input
              type="number"
              value={form.age}
              onChange={(e) => setForm({ ...form, age: e.target.value })}
            />
          </div>
          <div className="form-row">
            <label>Notes</label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
          {error && <p style={{ color: "var(--alert)" }}>{error}</p>}
          <button className="btn btn-primary" type="submit">
            Save profile
          </button>
        </form>
      </div>

      <div className="panel card">
        <h2>Profiles</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Age</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.elderly_code}</td>
                <td>{r.full_name}</td>
                <td>{r.age ?? "—"}</td>
                <td>{r.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
