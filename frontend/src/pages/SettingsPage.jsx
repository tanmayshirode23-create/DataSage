import { useState } from "react";
import { api } from "../api.js";

export default function SettingsPage({ user, onUserChange }) {
  const [threshold, setThreshold] = useState(String(user.alert_threshold));
  const [note, setNote] = useState({ text: "", error: false });
  const [busy, setBusy] = useState(false);

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setNote({ text: "", error: false });
    try {
      const updated = await api.updateSettings({ alert_threshold: Number(threshold) });
      onUserChange(updated);
      setNote({ text: "Alert level saved.", error: false });
    } catch (err) {
      setNote({ text: err.message, error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="narrow">
      <h1>Settings</h1>

      <section className="panel">
        <h2>Account</h2>
        <dl className="details">
          <div><dt>Name</dt><dd>{user.name}</dd></div>
          <div><dt>Email</dt><dd>{user.email}</dd></div>
        </dl>
      </section>

      <form className="panel" onSubmit={save}>
        <h2>Alert level</h2>
        <p className="hint">
          Files that score below this number are flagged on your dashboard and on their report.
        </p>
        <div className="inline">
          <input
            type="number" min="0" max="100" step="1" value={threshold}
            onChange={(e) => setThreshold(e.target.value)} aria-label="Alert score"
          />
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Save"}</button>
        </div>
        {note.text && <p className={note.error ? "error" : "hint"} role="status">{note.text}</p>}
      </form>
    </div>
  );
}
