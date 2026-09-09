import { useEffect, useState } from "react";
import { listObservations } from "../services/api";
import { attentionBadgeClass, formatAttention } from "../utils/labels";

export default function HistoryPage() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    listObservations({ limit: 100 }).then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <div>
      <h1 className="page-title">Monitoring history</h1>
      <p className="page-sub">Saved AI predictions of observable facial expressions (derived results only).</p>
      <div className="panel card">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Time</th>
              <th>Expression</th>
              <th>Confidence</th>
              <th>Session</th>
              <th>Attention</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => {
              const d = new Date(o.observed_at);
              return (
                <tr key={o.id}>
                  <td>{d.toLocaleDateString()}</td>
                  <td>{d.toLocaleTimeString()}</td>
                  <td>{o.expression}</td>
                  <td>{(o.confidence * 100).toFixed(1)}%</td>
                  <td>{o.session_id}</td>
                  <td>
                    <span className={attentionBadgeClass(o.attention_indicator)}>
                      {formatAttention(o.attention_indicator)}
                    </span>
                  </td>
                </tr>
              );
            })}
            {!rows.length && (
              <tr>
                <td colSpan={6}>No history yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
