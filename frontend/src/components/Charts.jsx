import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { SUMMARY_COLORS, formatDateTime } from "../utils.js";

const AXIS = { fontSize: 12, fill: "#4a5568" };
const GRID = "#e3e8ee";

export function IssueMixChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" tick={AXIS} allowDecimals={false} />
        <YAxis type="category" dataKey="issue" width={112} tick={AXIS} />
        <Tooltip cursor={{ fill: "#eef2f6" }} />
        <Bar dataKey="count" name="Issues" radius={[0, 3, 3, 0]}>
          {data.map((row) => <Cell key={row.issue} fill={SUMMARY_COLORS[row.issue] || "#64748b"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MissingChart({ data }) {
  const rows = data.filter((d) => d.count > 0).sort((a, b) => b.count - a.count);
  if (!rows.length) return <p className="muted">No missing values.</p>;
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, rows.length * 34 + 40)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" tick={AXIS} allowDecimals={false} />
        <YAxis type="category" dataKey="column" width={130} tick={AXIS} />
        <Tooltip cursor={{ fill: "#eef2f6" }} />
        <Bar dataKey="count" name="Missing" fill="#e0a800" radius={[0, 3, 3, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function StatusChart({ data }) {
  if (!data || !data.length) return <p className="muted">No status column was found.</p>;
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 30 + 40)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" tick={AXIS} allowDecimals={false} />
        <YAxis type="category" dataKey="status" width={150} tick={AXIS} />
        <Tooltip cursor={{ fill: "#eef2f6" }} />
        <Bar dataKey="count" name="Rows" fill="#2f8f6b" radius={[0, 3, 3, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DateTrendChart({ trend }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={trend.points} margin={{ left: 0, right: 16, top: 8, bottom: 4 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis dataKey="month" tick={AXIS} minTickGap={24} />
        <YAxis tick={AXIS} allowDecimals={false} width={40} />
        <Tooltip />
        <Line type="monotone" dataKey="count" name="Records" stroke="#0b7a75" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Score of the same file name over time (shown on the dashboard).
export function ScoreTrendChart({ series }) {
  const data = series.points.map((p) => ({ ...p, label: formatDateTime(p.uploaded_at) }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ left: 0, right: 16, top: 8, bottom: 4 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis dataKey="label" tick={AXIS} minTickGap={24} />
        <YAxis domain={[0, 100]} tick={AXIS} width={36} />
        <Tooltip />
        <Line type="monotone" dataKey="score" name="Score" stroke="#0b7a75" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
