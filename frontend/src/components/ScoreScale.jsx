import { ZONES } from "../utils.js";

// The score on a bar split into the four readiness zones the backend uses.
// Zone widths are proportional, so you can see how far a file is from "Launch ready".
export default function ScoreScale({ score }) {
  const position = Math.max(0, Math.min(100, score));
  return (
    <div className="scale">
      <div className="scale-bar" role="img" aria-label={`Score ${score} out of 100`}>
        {ZONES.map((zone) => (
          <span key={zone.label} style={{ width: `${zone.to - zone.from}%`, background: zone.color }} />
        ))}
        <i className="scale-marker" style={{ left: `${position}%` }} />
      </div>
      <div className="scale-ticks" aria-hidden="true">
        {[70, 85, 95].map((tick) => (
          <span key={tick} style={{ left: `${tick}%` }}>{tick}</span>
        ))}
      </div>
      <ul className="scale-legend">
        {ZONES.map((zone) => (
          <li key={zone.label}>
            <i style={{ background: zone.color }} />
            {zone.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
