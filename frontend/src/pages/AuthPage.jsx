import { useState } from "react";
import { api } from "../api.js";
import Logo from "../components/Logo.jsx";

const CHECKS = [
  "Missing values and blank fields",
  "Duplicate rows and repeated customer IDs",
  "Invalid email addresses and phone numbers",
  "Unreadable dates and inconsistent statuses",
];

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = isSignup
        ? await api.signup(form)
        : await api.login({ email: form.email, password: form.password });
      onAuth(result.access_token, result.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <section className="auth-brand">
        <div className="brand brand-light">
          <Logo size={34} />
          <span>DataSage</span>
        </div>
        <div>
          <h1>Know if your customer data is ready before you use it.</h1>
          <p>
            Upload a CSV and DataSage scores it out of 100, shows you the exact rows that need fixing,
            and gives you a short plan to clean them.
          </p>
          <ul className="auth-checks">
            {CHECKS.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
        <p className="auth-foot">Every upload is saved, so you can see whether a file is improving over time.</p>
      </section>

      <section className="auth-panel">
        <form className="auth-form" onSubmit={submit}>
          <h2>{isSignup ? "Create your account" : "Log in"}</h2>
          <p className="muted">
            {isSignup ? "It takes less than a minute." : "Welcome back. Enter your details to continue."}
          </p>

          {isSignup && (
            <label>
              Name
              <input value={form.name} onChange={set("name")} autoComplete="name" required />
            </label>
          )}
          <label>
            Email
            <input type="email" value={form.email} onChange={set("email")} autoComplete="email" required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={set("password")}
              autoComplete={isSignup ? "new-password" : "current-password"}
              minLength={isSignup ? 6 : undefined}
              required
            />
            {isSignup && <span className="hint">At least 6 characters.</span>}
          </label>

          {error && <p className="error" role="alert">{error}</p>}

          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Please wait..." : isSignup ? "Create account" : "Log in"}
          </button>

          <p className="switch">
            {isSignup ? "Already have an account?" : "New to DataSage?"}{" "}
            <button type="button" className="link" onClick={() => { setMode(isSignup ? "login" : "signup"); setError(""); }}>
              {isSignup ? "Log in" : "Create an account"}
            </button>
          </p>
        </form>
      </section>
    </div>
  );
}
