import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { ISSUE_TYPES, formatNumber } from "../utils.js";

export default function RowsTab({ datasetId, truncated }) {
  const [view, setView] = useState("preview");
  return (
    <div>
      <div className="segmented" role="tablist" aria-label="Row view">
        <button role="tab" aria-selected={view === "preview"} onClick={() => setView("preview")}>Data preview</button>
        <button role="tab" aria-selected={view === "issues"} onClick={() => setView("issues")}>Issue list</button>
      </div>
      {view === "preview" ? <Preview datasetId={datasetId} /> : <IssueList datasetId={datasetId} truncated={truncated} />}
    </div>
  );
}

function Preview({ datasetId }) {
  const [rows, setRows] = useState(25);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setData(null);
    api.preview(datasetId, rows)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [datasetId, rows]);

  return (
    <div>
      <div className="toolbar">
        <label className="inline">
          Rows shown
          <select value={rows} onChange={(e) => setRows(Number(e.target.value))}>
            {[25, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <ul className="key">
          {Object.entries(ISSUE_TYPES).map(([key, t]) => (
            <li key={key}><i style={{ background: t.tint, borderColor: t.color }} />{t.label}</li>
          ))}
        </ul>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {!data && !error && <p className="muted">Loading...</p>}
      {data && (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Row</th>
                {data.columns.map((c) => <th key={c}>{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => {
                const wholeRow = row.issues.find((i) => i.column === "(whole row)");
                return (
                  <tr key={row.row_number}>
                    <th scope="row" style={wholeRow ? { background: ISSUE_TYPES[wholeRow.issue_type].tint } : undefined}
                        title={wholeRow ? ISSUE_TYPES[wholeRow.issue_type].label : undefined}>
                      {row.row_number}
                    </th>
                    {data.columns.map((c) => {
                      const hit = row.issues.find((i) => i.column === c);
                      const type = hit && ISSUE_TYPES[hit.issue_type];
                      return (
                        <td key={c} style={type ? { background: type.tint, boxShadow: `inset 3px 0 0 ${type.color}` } : undefined}
                            title={type ? type.label : undefined}>
                          {row.values[c] ?? ""}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function IssueList({ datasetId, truncated }) {
  const [issueType, setIssueType] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const pageSize = 25;

  const load = useCallback(() => {
    setData(null);
    api.issues(datasetId, { issue_type: issueType, page, page_size: pageSize })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [datasetId, issueType, page]);

  useEffect(() => { load(); }, [load]);

  const pages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div>
      <div className="toolbar">
        <label className="inline">
          Show
          <select value={issueType} onChange={(e) => { setIssueType(e.target.value); setPage(1); }}>
            <option value="">All issues</option>
            {Object.entries(ISSUE_TYPES).map(([key, t]) => <option key={key} value={key}>{t.label}</option>)}
          </select>
        </label>
        {data && <span className="muted">{formatNumber(data.total)} found</span>}
      </div>
      {truncated && (
        <p className="hint">
          This file has a very large number of issues, so only the first batch is listed here.
          Counts and the score still include everything.
        </p>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {!data && !error && <p className="muted">Loading...</p>}
      {data && data.items.length === 0 && <p className="empty">No issues of this kind.</p>}
      {data && data.items.length > 0 && (
        <>
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Row</th><th>Column</th><th>Issue</th><th>Value</th></tr></thead>
              <tbody>
                {data.items.map((item, index) => (
                  <tr key={`${item.row_number}-${item.column}-${item.issue_type}-${index}`}>
                    <th scope="row">{item.row_number}</th>
                    <td>{item.column}</td>
                    <td>
                      <span className="chip">
                        <i style={{ background: ISSUE_TYPES[item.issue_type]?.color }} />
                        {ISSUE_TYPES[item.issue_type]?.label || item.issue_type}
                      </span>
                    </td>
                    <td className={item.value ? "" : "muted"}>{item.value || "(blank)"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
            <span>Page {page} of {pages}</span>
            <button className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  );
}
