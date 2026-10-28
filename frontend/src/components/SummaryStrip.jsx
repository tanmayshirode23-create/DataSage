import { formatNumber } from "../utils.js";

// Four headline numbers across all of the user's datasets.
export default function SummaryStrip({ datasets }) {
  const count = datasets.length;
  const average = count ? datasets.reduce((sum, d) => sum + d.quality_score, 0) / count : 0;
  const flagged = datasets.filter((d) => d.below_threshold).length;
  const issues = datasets.reduce((sum, d) => sum + d.issue_count, 0);

  const items = [
    { label: "Files checked", value: formatNumber(count) },
    { label: "Average score", value: average.toFixed(1) },
    { label: "Below your alert level", value: formatNumber(flagged), warn: flagged > 0 },
    { label: "Issues found", value: formatNumber(issues) },
  ];

  return (
    <dl className="summary" aria-label="Summary of all datasets">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd className={item.warn ? "warn" : ""}>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
