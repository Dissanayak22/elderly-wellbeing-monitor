import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAnalytics } from "../services/api";
import { countActionableAttention, formatAttention } from "../utils/labels";

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getAnalytics()
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to load analytics. " + (err.message || ""));
        setData(null);
        setLoading(false);
      });
  }, []);

  if (loading)
    return (
      <div>
        <h1 className="page-title">Analytics</h1>
        <p className="page-sub">Loading analytics data...</p>
        <div className="panel card" style={{ textAlign: "center", padding: "2rem" }}>
          <p>⏳ Fetching analytics...</p>
        </div>
      </div>
    );

  if (error)
    return (
      <div>
        <h1 className="page-title">Analytics</h1>
        <p className="page-sub">Distribution and trends of AI expression predictions — not clinical outcomes.</p>
        <div className="panel card" style={{ textAlign: "center", padding: "2rem" }}>
          <p style={{ color: "var(--alert)" }}>❌ {error}</p>
        </div>
      </div>
    );

  if (!data || data.observation_count === 0)
    return (
      <div>
        <h1 className="page-title">Analytics</h1>
        <p className="page-sub">Distribution and trends of AI expression predictions — not clinical outcomes.</p>
        <div className="panel card" style={{ textAlign: "center", padding: "2rem" }}>
          <p>📊 No observation data yet. Start monitoring sessions to collect data.</p>
        </div>
      </div>
    );

  const dist = Object.entries(data.expression_distribution || {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
  
  const days = Object.keys(data.daily_trends || {}).sort();
  const trend = days.map((day) => {
    const exprs = data.daily_trends[day];
    return { day, count: Object.values(exprs).reduce((a, b) => a + b, 0) };
  });

  const attentionStats = data.attention_counts || {};
  const attentionTotal = Object.values(attentionStats).reduce((a, b) => a + b, 0) || 1;
  const attentionData = Object.entries(attentionStats).map(([name, value]) => ({
    name: formatAttention(name),
    value,
    percentage: ((value / attentionTotal) * 100).toFixed(1),
  }));
  const actionableAttention = countActionableAttention(attentionStats);

  const COLORS = ["#1f7a74", "#f39c12", "#e74c3c", "#27ae60", "#2980b9", "#9b59b6"];

  return (
    <div>
      <h1 className="page-title">Analytics</h1>
      <p className="page-sub">Distribution and trends of AI expression predictions — not clinical outcomes.</p>

      <div className="grid-stats">
        <div className="stat card">
          <h3>Total Observations</h3>
          <p style={{ fontSize: "2rem", fontWeight: "700", color: "var(--teal)" }}>{data.observation_count}</p>
          <p className="stat-subtext">expressions recorded</p>
        </div>
        <div className="stat card">
          <h3>Avg. Model Confidence</h3>
          <p style={{ fontSize: "2rem", fontWeight: "700", color: "var(--teal)" }}>
            {(data.average_confidence * 100).toFixed(1)}%
          </p>
          <p className="stat-subtext">mean model confidence, not accuracy</p>
        </div>
        <div className="stat card">
          <h3>Actionable Attention Flags</h3>
          <p style={{ fontSize: "2rem", fontWeight: "700", color: "var(--alert)" }}>
            {actionableAttention}
          </p>
          <p className="stat-subtext">({(((actionableAttention / attentionTotal) * 100) || 0).toFixed(1)}%)</p>
        </div>
        <div className="stat card">
          <h3>Monitoring Days</h3>
          <p style={{ fontSize: "2rem", fontWeight: "700", color: "var(--teal)" }}>{days.length}</p>
          <p className="stat-subtext">active monitoring periods</p>
        </div>
      </div>

      <div className="panel card">
        <h2>Expression Distribution</h2>
        {dist.length > 0 ? (
          <div style={{ width: "100%", height: 300, display: "flex", gap: "2rem" }}>
            <div style={{ flex: 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dist}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis allowDecimals={false} />
                  <Tooltip formatter={(value) => `${value} observations`} />
                  <Bar dataKey="value" fill="#1f7a74" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ flex: 0.5, minWidth: "150px" }}>
              <div style={{ fontSize: "0.9rem", lineHeight: "1.8" }}>
                <strong>Breakdown:</strong>
                {dist.map((item, idx) => (
                  <div key={idx} style={{ paddingTop: "0.5rem", borderTop: "1px solid var(--line)" }}>
                    <div style={{ fontWeight: "600" }}>{item.name}</div>
                    <div style={{ color: "var(--muted)" }}>
                      {item.value} ({((item.value / data.observation_count) * 100).toFixed(1)}%)
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p style={{ textAlign: "center", color: "var(--muted)" }}>No expression data available</p>
        )}
      </div>

      <div className="panel card">
        <h2>Daily Observation Trend</h2>
        {trend.length > 0 ? (
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" angle={-45} textAnchor="end" height={80} />
                <YAxis allowDecimals={false} />
                <Tooltip formatter={(value) => `${value} observations`} />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#1f7a74"
                  strokeWidth={3}
                  dot={{ r: 5, fill: "#155e59" }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p style={{ textAlign: "center", color: "var(--muted)" }}>No trend data available</p>
        )}
      </div>

      <div className="panel card">
        <h2>Attention Status Distribution</h2>
        {attentionData.length > 0 ? (
          <div style={{ width: "100%", height: 300, display: "flex", gap: "2rem", alignItems: "center" }}>
            <div style={{ flex: 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={attentionData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percentage }) => `${name} (${percentage}%)`}
                  >
                    {attentionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `${value} observations`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ flex: 0.5, minWidth: "150px" }}>
              <div style={{ fontSize: "0.9rem", lineHeight: "1.8" }}>
                <strong>Status Summary:</strong>
                {attentionData.map((item, idx) => (
                  <div key={idx} style={{ paddingTop: "0.5rem", borderTop: "1px solid var(--line)" }}>
                    <div style={{ fontWeight: "600" }}>{item.name}</div>
                    <div style={{ color: "var(--muted)" }}>
                      {item.value} observations
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p style={{ textAlign: "center", color: "var(--muted)" }}>No attention data available</p>
        )}
      </div>
    </div>
  );
}
