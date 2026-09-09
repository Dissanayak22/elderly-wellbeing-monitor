import { useEffect, useState } from "react";
import { createReport, exportReport, listElderly, listReports } from "../services/api";

export default function ReportsPage() {
  const [profiles, setProfiles] = useState([]);
  const [reports, setReports] = useState([]);
  const [elderlyId, setElderlyId] = useState("");
  const [title, setTitle] = useState("Monitoring summary");

  async function refresh() {
    const [p, r] = await Promise.all([listElderly(), listReports()]);
    setProfiles(p);
    setReports(r);
    if (!elderlyId && p[0]) setElderlyId(String(p[0].id));
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function onCreate() {
    await createReport({ elderly_id: Number(elderlyId), title });
    await refresh();
  }

  async function onExport(id) {
    const data = await exportReport(id);
    const blob = new Blob([data.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h1 className="page-title">Reports</h1>
      <p className="page-sub">Simple monitoring reports for caregivers (research/support wording).</p>

      <div className="panel card">
        <h2>Generate report</h2>
        <div className="form-row">
          <label>Elderly profile</label>
          <select value={elderlyId} onChange={(e) => setElderlyId(e.target.value)}>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="button" onClick={onCreate} disabled={!elderlyId}>
          Create report
        </button>
      </div>

      <div className="panel card">
        <h2>Saved reports</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Created</th>
              <th>Summary</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id}>
                <td>{r.title}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>{r.summary?.slice(0, 80)}…</td>
                <td>
                  <button className="btn btn-secondary" type="button" onClick={() => onExport(r.id)}>
                    Export
                  </button>
                </td>
              </tr>
            ))}
            {!reports.length && (
              <tr>
                <td colSpan={4}>No reports yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
