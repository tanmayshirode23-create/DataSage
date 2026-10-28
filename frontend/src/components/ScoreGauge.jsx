import { zoneFor } from "../utils.js";

// A 270-degree ring that fills to the score. Its color follows the readiness zone.
export default function ScoreGauge({ score, size = 190 }) {
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const arc = circumference * 0.75; // the visible part of the ring
  const value = Math.max(0, Math.min(100, score));
  const zone = zoneFor(score);

  return (
    <div className="gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Score ${score} out of 100`}>
        <g transform={`rotate(135 ${size / 2} ${size / 2})`} fill="none" strokeWidth={stroke} strokeLinecap="round">
          <circle cx={size / 2} cy={size / 2} r={radius} stroke="#e4e9ef" strokeDasharray={`${arc} ${circumference}`} />
          <circle
            cx={size / 2} cy={size / 2} r={radius} stroke={zone.strong}
            strokeDasharray={`${(arc * value) / 100} ${circumference}`}
          />
        </g>
      </svg>
      <div className="gauge-center">
        <span className="gauge-value">{score}</span>
        <span className="gauge-of">out of 100</span>
      </div>
    </div>
  );
}
