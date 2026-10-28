import { formatNumber } from "../utils.js";

function Section({ title, note, children }) {
  return (
    <section className="check">
      <h3>{title}</h3>
      {note && <p className="hint">{note}</p>}
      {children}
    </section>
  );
}

function CountTable({ rows, empty, columnLabel = "Column" }) {
  if (!rows.length) return <p className="muted">{empty}</p>;
  return (
    <div className="table-wrap">
      <table className="data compact">
        <thead><tr><th>{columnLabel}</th><th className="num">Problems</th></tr></thead>
        <tbody>
          {rows.map(([name, count]) => (
            <tr key={name}><td>{name}</td><td className="num">{formatNumber(count)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ChecksTab({ report }) {
  const total = report.total_rows || 1;
  const missing = report.missing_by_column.filter((c) => c.count > 0).sort((a, b) => b.count - a.count);
  const status = report.status;
  const flaggedStatuses = status.table.filter((r) => r.issue_type !== "Looks good");
  const okStatuses = status.table.length - flaggedStatuses.length;

  return (
    <div className="checks">
      <Section title="Missing values" note="Cells that are empty or contain only spaces.">
        {missing.length === 0 ? <p className="muted">Nothing is missing.</p> : (
          <div className="table-wrap">
            <table className="data compact">
              <thead><tr><th>Column</th><th className="num">Missing</th><th className="num">Of all rows</th></tr></thead>
              <tbody>
                {missing.map((c) => (
                  <tr key={c.column}>
                    <td>{c.column}</td>
                    <td className="num">{formatNumber(c.count)}</td>
                    <td className="num">{((c.count / total) * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Duplicates" note="Exact copies of another row, and ID values that appear more than once.">
        <dl className="facts">
          <div><dt>Duplicate rows</dt><dd>{formatNumber(report.duplicate_rows)}</dd></div>
          <div>
            <dt>Duplicate IDs{report.detected_columns.id_column ? ` (${report.detected_columns.id_column})` : ""}</dt>
            <dd>{report.detected_columns.id_column ? formatNumber(report.duplicate_ids) : "No ID column"}</dd>
          </div>
        </dl>
      </Section>

      <Section title="Emails and phone numbers" note="An email needs a name, an @ and a domain. A phone number needs 7 to 15 digits once spaces and dashes are removed.">
        <h4>Invalid emails</h4>
        <CountTable rows={Object.entries(report.invalid_emails)} empty="No email column was found." />
        <h4>Invalid phone numbers</h4>
        <CountTable rows={Object.entries(report.invalid_phones)} empty="No phone column was found." />
      </Section>

      <Section title="Dates" note="Dates that are blank, or cannot be read as a date.">
        {Object.keys(report.dates).length === 0 ? <p className="muted">No date column was found.</p> : (
          <div className="table-wrap">
            <table className="data compact">
              <thead><tr><th>Column</th><th className="num">Blank</th><th className="num">Unreadable</th></tr></thead>
              <tbody>
                {Object.entries(report.dates).map(([col, r]) => (
                  <tr key={col}><td>{col}</td><td className="num">{formatNumber(r.missing)}</td><td className="num">{formatNumber(r.invalid)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section
        title="Statuses"
        note={status.column
          ? `Values in ${status.column} compared with the standard list (Not Started, Pending, In Progress, Blocked, Waiting on Customer, On Hold, Completed, Cancelled).`
          : "No status column was found."}
      >
        {status.column && (
          <>
            <dl className="facts">
              <div><dt>Blank</dt><dd>{formatNumber(status.missing)}</dd></div>
              <div><dt>Wrong spelling or case</dt><dd>{formatNumber(status.label_mismatch)}</dd></div>
              <div><dt>Not on the list</dt><dd>{formatNumber(status.non_standard)}</dd></div>
            </dl>
            {flaggedStatuses.length > 0 && (
              <div className="table-wrap">
                <table className="data compact">
                  <thead><tr><th>Current value</th><th>Suggested value</th><th className="num">Rows</th><th>Problem</th></tr></thead>
                  <tbody>
                    {flaggedStatuses.slice(0, 60).map((r, i) => (
                      <tr key={i}>
                        <td>{r.current_value || "(blank)"}</td>
                        <td>{r.recommended_value}</td>
                        <td className="num">{formatNumber(r.rows)}</td>
                        <td>{r.issue_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {flaggedStatuses.length > 60 && <p className="hint">Showing the first 60 of {flaggedStatuses.length} values.</p>}
            <p className="hint">{okStatuses} value{okStatuses === 1 ? "" : "s"} already match the standard list.</p>
          </>
        )}
      </Section>
    </div>
  );
}
