import { useRef, useState } from "react";
import { api } from "../api.js";

const splitList = (text) => text.split(",").map((s) => s.trim()).filter(Boolean);

export default function UploadPanel({ onDone }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rules, setRules] = useState({ email: "", phone: "", date: "", id: "", status: "" });

  const setRule = (key) => (event) => setRules({ ...rules, [key]: event.target.value });

  function buildRules() {
    const out = {};
    if (rules.email.trim()) out.email_columns = splitList(rules.email);
    if (rules.phone.trim()) out.phone_columns = splitList(rules.phone);
    if (rules.date.trim()) out.date_columns = splitList(rules.date);
    if (rules.id.trim()) out.id_column = rules.id.trim();
    if (rules.status.trim()) out.status_column = rules.status.trim();
    return out;
  }

  async function run(task) {
    setError("");
    setBusy(true);
    try {
      onDone(await task());
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  function pick(selected) {
    if (!selected) return;
    setFile(selected);
    setError("");
  }

  return (
    <section className="panel">
      <h2>Check a file</h2>

      <label
        className={`drop ${dragging ? "drop-active" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]); }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => pick(e.target.files[0])}
        />
        {file ? <strong>{file.name}</strong> : <span>Drop a CSV here, or click to choose one</span>}
      </label>

      <details className="rules">
        <summary>Set column rules (optional)</summary>
        <p className="hint">
          Columns are found by name (for example, anything with "email" in it). If yours are named
          differently, list them here, separated by commas.
        </p>
        <label>Email columns<input value={rules.email} onChange={setRule("email")} placeholder="Auto-detected" /></label>
        <label>Phone columns<input value={rules.phone} onChange={setRule("phone")} placeholder="Auto-detected" /></label>
        <label>Date columns<input value={rules.date} onChange={setRule("date")} placeholder="Auto-detected" /></label>
        <label>ID column<input value={rules.id} onChange={setRule("id")} placeholder="customer_id" /></label>
        <label>Status column<input value={rules.status} onChange={setRule("status")} placeholder="onboarding_status" /></label>
      </details>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="actions">
        <button className="btn btn-primary" disabled={!file || busy} onClick={() => run(() => api.upload(file, buildRules()))}>
          {busy ? "Checking..." : "Check this file"}
        </button>
        <button className="btn" disabled={busy} onClick={() => run(() => api.uploadSample())}>
          Try the sample data
        </button>
      </div>
    </section>
  );
}
