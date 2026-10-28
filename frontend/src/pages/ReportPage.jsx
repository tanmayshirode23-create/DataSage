import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { DateTrendChart, IssueMixChart, MissingChart, StatusChart } from "../components/Charts.jsx";
import ChecksTab from "../components/ChecksTab.jsx";
import PlanTab from "../components/PlanTab.jsx";
import RowsTab from "../components/RowsTab.jsx";
import ScoreGauge from "../components/ScoreGauge.jsx";
import ScoreScale from "../components/ScoreScale.jsx";
import { ReportSkeleton } from "../components/Skeleton.jsx";
import { formatDateTime, formatNumber } from "../utils.js";

const TABS = [
  ["overview", "Overview"],
  ["rows", "Rows"],
  ["checks", "Checks"],
  ["plan", "Cleanup plan"],
];

export default function ReportPage() {
  const { id } = useParams();
  const [dataset, setDataset] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setDataset(null);
    setError("");
    api.getDataset(id)
      .then((d) => { if (!cancelled) setDataset(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [id]);

  const download = useCallback(async () => {
    setDownloading(true);
    try {
      await api.downloadCleaned(id);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  }, [id]);

  if (error && !dataset) {
    return (
      <div>
        <p className="error" role="alert">{error}</p>
        <Link to="/">Back to your datasets</Link>
      </div>
    );
  }
  if (!dataset) return <ReportSkeleton />;

  const { report } = dataset;

  return (
    <div className="report">
      <Link to="/" className="back">All datasets</Link>

      <header className="report-head">
        <div>
          <h1>{dataset.filename}</h1>
          <p className="muted">
            {formatNumber(dataset.total_rows)} rows, {dataset.total_columns} columns, checked {formatDateTime(dataset.uploaded_at)}
          </p>
        </div>
        <button className="btn" onClick={download} disabled={downloading}>
          {downloading ? "Preparing..." : "Download cleaned CSV"}
        </button>
      </header>
      {error && <p className="error" role="alert">{error}</p>}

      <section className="score-block" aria-label="Quality score">
        <ScoreGauge score={dataset.quality_score} />
        <div className="score-detail">
          <h2>{dataset.score_label}</h2>
          <p className="muted">
            {formatNumber(dataset.issue_count)} issues found across {formatNumber(dataset.total_rows * dataset.total_columns)} cells.
          </p>
          {dataset.below_threshold && <p className="flag-line">Below your alert level.</p>}
          <ScoreScale score={dataset.quality_score} />
        </div>
      </section>

      <div className="tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="overview">
          <div>
            <h3>Issues by type</h3>
            <IssueMixChart data={report.issue_summary} />
          </div>
          <div>
            <h3>Missing values by column</h3>
            <MissingChart data={report.missing_by_column} />
          </div>
          <div>
            <h3>{report.status.column ? `Values in ${report.status.column}` : "Status values"}</h3>
            <StatusChart data={report.status.distribution} />
          </div>
          {report.date_trend && (
            <div>
              <h3>Records over time by {report.date_trend.column}</h3>
              <DateTrendChart trend={report.date_trend} />
            </div>
          )}
        </div>
      )}
      {tab === "rows" && <RowsTab datasetId={dataset.id} truncated={report.issues_truncated} />}
      {tab === "checks" && <ChecksTab report={report} />}
      {tab === "plan" && <PlanTab report={report} onDownload={download} downloading={downloading} />}
    </div>
  );
}
