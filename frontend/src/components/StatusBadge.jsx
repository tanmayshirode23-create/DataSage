import { zoneFor } from "../utils.js";

// A small colored label for a score, e.g. "Needs light cleanup".
export default function StatusBadge({ score, label }) {
  const zone = zoneFor(score);
  return (
    <span className="badge" style={{ background: zone.soft, color: zone.text }}>
      <i style={{ background: zone.strong }} />
      {label || zone.label}
    </span>
  );
}
