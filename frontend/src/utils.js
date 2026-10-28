// Colors for each kind of problem (same palette as the original Streamlit dashboard).
export const ISSUE_TYPES = {
  missing_value: { label: "Missing value", color: "#facc15", tint: "#fef7cc" },
  duplicate_row: { label: "Duplicate row", color: "#fb7185", tint: "#ffe3e7" },
  duplicate_id: { label: "Duplicate ID", color: "#f97316", tint: "#ffe6d3" },
  invalid_email: { label: "Invalid email", color: "#38bdf8", tint: "#dcf2fd" },
  invalid_phone: { label: "Invalid phone", color: "#2563eb", tint: "#dbe6fc" },
  invalid_date: { label: "Date issue", color: "#a78bfa", tint: "#e9e3fd" },
  status_issue: { label: "Status issue", color: "#22c55e", tint: "#d9f5e3" },
};

// Same colors keyed by the names used in the report's issue_summary.
export const SUMMARY_COLORS = {
  "Missing values": "#facc15",
  "Duplicate rows": "#fb7185",
  "Duplicate IDs": "#f97316",
  "Invalid emails": "#38bdf8",
  "Invalid phones": "#2563eb",
  "Date issues": "#a78bfa",
  "Status issues": "#22c55e",
};

// The four readiness zones, as used by the backend's score_label().
export const ZONES = [
  { from: 0, to: 70, label: "Migration risk", color: "#e5a29b" },
  { from: 70, to: 85, label: "Needs focused cleanup", color: "#ecc57d" },
  { from: 85, to: 95, label: "Needs light cleanup", color: "#9fd0c4" },
  { from: 95, to: 100, label: "Launch ready", color: "#5fb394" },
];

// Readiness zone for a score, with strong (text, gauge) and soft (badge background) colors.
const ZONE_STYLES = [
  { strong: "#b42318", soft: "#fbe9e7", text: "#8f1d12" },
  { strong: "#b7791f", soft: "#fcf1d9", text: "#7a5200" },
  { strong: "#0b7a75", soft: "#dff1ee", text: "#0a5e59" },
  { strong: "#1f8a5b", soft: "#dcf3e7", text: "#14603f" },
];
export function zoneFor(score) {
  const index = score >= 95 ? 3 : score >= 85 ? 2 : score >= 70 ? 1 : 0;
  return { ...ZONES[index], ...ZONE_STYLES[index] };
}

// The server stores UTC without a "Z"; add it so the browser shows local time.
export function parseServerDate(value) {
  if (!value) return null;
  return new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
}

export function formatDate(value) {
  const date = parseServerDate(value);
  if (!date || Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value) {
  const date = parseServerDate(value);
  if (!date || Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export const formatNumber = (n) => Number(n || 0).toLocaleString();
