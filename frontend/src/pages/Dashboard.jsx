import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { ScoreTrendChart } from "../components/Charts.jsx";
import { ListSkeleton } from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import SummaryStrip from "../components/SummaryStrip.jsx";
import UploadPanel from "../components/UploadPanel.jsx";
import { formatDateTime, formatNumber } from "../utils.js";

export default function Dashboard() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState(null);
  const [trends, setTrends] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [list, series] = await Promise.all([api.listDatasets(), api.trends()]);
      setDatasets(list);
      setTrends(series);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function remove(dataset) {
    if (!window.confirm(`Delete "${dataset.filename}" and its report?`)) return;
    try {
      await api.deleteDataset(dataset.id);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const trendSeries = trends.find((s) => s.points.length >= 2);

  return (
    <div>
      <header className="page-head">
        <h1>Datasets</h1>
        <p className="muted">Every file you have checked, newest first.</p>
      </header>

      {datasets && datasets.length > 0 && <SummaryStrip datasets={datasets} />}

      <div className="dash">
        <div className="dash-side">
          <UploadPanel onDone={(dataset) => navigate(`/datasets/${dataset.id}`)} />
        </div>

        <div className="dash-main">
          <section>
            <h2>Recent checks</h2>
            {error && <p className="error" role="alert">{error}</p>}
            {datasets === null && !error && <ListSkeleton />}
            {datasets && datasets.length === 0 && (
              <p className="empty">
                Nothing checked yet. Drop a CSV into the box on the left, or try the sample data to see what a report looks like.
              </p>
            )}
            {datasets && datasets.length > 0 && (
              <ul className="ledger">
                {datasets.map((d) => (
                  <li key={d.id}>
                    <Link to={`/datasets/${d.id}`} className="ledger-main">
                      <span className="ledger-name">{d.filename}</span>
                      <span className="ledger-meta">
                        {formatDateTime(d.uploaded_at)}, {formatNumber(d.total_rows)} rows, {formatNumber(d.issue_count)} issues
                      </span>
                    </Link>
                    <div className="ledger-score">
                      <strong>{d.quality_score}</strong>
                      <StatusBadge score={d.quality_score} label={d.score_label} />
                      {d.below_threshold && <em className="flag">Below your alert level</em>}
                    </div>
                    <button className="btn btn-quiet" onClick={() => remove(d)} aria-label={`Delete ${d.filename}`}>
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <h2>Score over time</h2>
            {trendSeries ? (
              <>
                <p className="hint">{trendSeries.filename}, {trendSeries.points.length} checks</p>
                <ScoreTrendChart series={trendSeries} />
              </>
            ) : (
              <p className="muted">
                Check a file with the same name more than once and its score history will appear here.
              </p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
