import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./layout.css";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/profiles", label: "Profiles" },
  { to: "/live", label: "Live Monitoring" },
  { to: "/history", label: "History" },
  { to: "/analytics", label: "Analytics" },
  { to: "/reports", label: "Reports" },
  { to: "/settings", label: "Settings" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar card">
        <div className="brand">
          <p className="brand-kicker">Caregiver console</p>
          <h1>Wellbeing Monitor</h1>
          <p className="brand-sub">Observable expression AI predictions</p>
        </div>
        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p>{user?.full_name}</p>
          <p className="muted">{user?.role}</p>
          <button className="btn btn-secondary" type="button" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <p className="disclaimer">
            Research / support tool. Not a medical diagnosis. Displays AI predictions of observable facial expressions
            with confidence scores and caregiver attention indicators.
          </p>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
