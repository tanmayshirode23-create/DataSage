import { useCallback, useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { session, setUnauthorizedHandler } from "./api.js";
import Logo from "./components/Logo.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ReportPage from "./pages/ReportPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";

function Sidebar({ user, onSignOut }) {
  return (
    <aside className="sidebar">
      <NavLink to="/" className="brand" aria-label="DataSage home">
        <Logo />
        <span>DataSage</span>
      </NavLink>

      <nav aria-label="Main">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
          Datasets
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
          Settings
        </NavLink>
      </nav>

      <div className="sidebar-user">
        <div className="avatar" aria-hidden="true">{user.name.trim().charAt(0).toUpperCase()}</div>
        <div className="sidebar-user-text">
          <strong>{user.name}</strong>
          <span>{user.email}</span>
        </div>
        <button className="btn-signout" onClick={onSignOut}>Log out</button>
      </div>
    </aside>
  );
}

export default function App() {
  const [user, setUser] = useState(() => (session.token() ? session.user() : null));
  const navigate = useNavigate();

  const signIn = useCallback((token, nextUser) => {
    session.save(token, nextUser);
    setUser(nextUser);
    navigate("/");
  }, [navigate]);

  const signOut = useCallback(() => {
    session.clear();
    setUser(null);
    navigate("/login");
  }, [navigate]);

  const updateUser = useCallback((nextUser) => {
    session.saveUser(nextUser);
    setUser(nextUser);
  }, []);

  // If the server says our login expired, go back to the login page.
  useEffect(() => { setUnauthorizedHandler(signOut); }, [signOut]);

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<AuthPage onAuth={signIn} />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    );
  }

  return (
    <div className="shell">
      <Sidebar user={user} onSignOut={signOut} />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard user={user} />} />
          <Route path="/datasets/:id" element={<ReportPage />} />
          <Route path="/settings" element={<SettingsPage user={user} onUserChange={updateUser} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
