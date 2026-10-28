export default function PlanTab({ report, onDownload, downloading }) {
  return (
    <div className="plan">
      <section>
        <h3>What to fix, in order</h3>
        <ol className="steps">
          {report.recommendations.map((rec, index) => (
            <li key={index} className={`prio prio-${rec.priority.toLowerCase()}`}>
              <div>
                <strong>{rec.title}</strong>
                <p>{rec.detail}</p>
              </div>
              <span className="prio-tag">{rec.priority} priority</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel">
        <h3>Get a cleaned copy</h3>
        <p>The cleaned file fixes what is safe to fix automatically:</p>
        <ul className="plain">
          <li>trims extra spaces around text and writes emails in lowercase</li>
          <li>writes readable dates as YYYY-MM-DD (dates that cannot be read are left blank)</li>
          <li>uses the standard spelling for known statuses</li>
          <li>removes exact duplicate rows and repeated IDs, keeping the first one</li>
        </ul>
        <p className="hint">
          It does not guess at invalid phone numbers, blank fields or unknown statuses. Those need someone who knows the right answer.
        </p>
        <button className="btn btn-primary" onClick={onDownload} disabled={downloading}>
          {downloading ? "Preparing..." : "Download cleaned CSV"}
        </button>
      </section>
    </div>
  );
}
