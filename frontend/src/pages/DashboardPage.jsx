import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboard } from "../services/api";
import { countActionableAttention, formatAttention } from "../utils/labels";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboard()
      .then(setStats)
      .catch(() => setError("Could not load dashboard."));
  }, []);

  if (error) return <p>{error}</p>;
  if (!stats) return <p>Loading dashboard…</p>;

  const chartData = Object.entries(stats.expression_distribution || {}).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">Overview of resident profiles, active monitoring sessions, and daily expression observations.</p>

      <div className="grid-stats">
        <div className="stat card">
          <h3>Elderly profiles</h3>
          <p>{stats.total_elderly_profiles}</p>
        </div>
        <div className="stat card">
          <h3>Today&apos;s sessions</h3>
          <p>{stats.today_sessions}</p>
        </div>
        <div className="stat card">
          <h3>Attention flags</h3>
          <p>{countActionableAttention(stats.attention_counts)}</p>
        </div>
      </div>

      <div className="panel card">
        <h2>Expression Distribution & Observations</h2>
        {chartData.length === 0 ? (
          <p className="disclaimer">No saved observations yet. Start live monitoring to collect data.</p>
        ) : (
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <BarChart data={chartData}>
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#1f7a74" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="panel card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
          <h2>Recent Expression Observations</h2>
          <Link className="btn btn-secondary" to="/live">
            Open live monitoring
          </Link>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Expression</th>
              <th>Confidence</th>
              <th>Attention</th>
              <th>Session</th>
            </tr>
          </thead>
          <tbody>
            {(stats.recent_observations || []).map((o) => (
              <tr key={o.id}>
                <td>{new Date(o.observed_at).toLocaleString()}</td>
                <td>{o.expression}</td>
                <td>{(o.confidence * 100).toFixed(1)}%</td>
                <td>{formatAttention(o.attention_indicator)}</td>
                <td>{o.session_id}</td>
              </tr>
            ))}
            {!stats.recent_observations?.length && (
              <tr>
                <td colSpan={5}>No observations yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="disclaimer">{stats.disclaimer}</p>
    </div>
  );
}
