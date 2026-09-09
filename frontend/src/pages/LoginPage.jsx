import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getApiError } from "../services/api";
import "./login.css";

export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("caregiver@wellbeing.care");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("Caregiver123!");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function toggleMode(signUpMode) {
    setIsSignUp(signUpMode);
    setError("");
    if (signUpMode) {
      if (email === "caregiver@wellbeing.care" || email === "caregiver@demo.example.com") setEmail("");
      if (password === "Caregiver123!") setPassword("");
    } else {
      setEmail("caregiver@wellbeing.care");
      setPassword("Caregiver123!");
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (isSignUp) {
        await register(email, fullName, password);
      } else {
        await login(email, password);
      }
      navigate("/");
    } catch (err) {
      const msg = getApiError(err, isSignUp ? "Registration failed." : "Login failed. Check email/password.");
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <section className="login-hero">
        <p className="brand-kicker">Caregiver Portal</p>
        <h1>Elderly Wellbeing & Expression Monitor</h1>
        <p>
          Professional observational platform for live monitoring of facial expressions, tracking daily wellbeing indicators and supporting proactive elderly care.
        </p>
        <p className="disclaimer">
          This system monitors observable facial expressions to assist caregiver monitoring. It does not provide medical diagnoses or psychiatric evaluations.
        </p>
      </section>

      <form className="login-card card" onSubmit={onSubmit}>
        <div className="auth-tabs">
          <button
            type="button"
            className={`tab-btn ${!isSignUp ? "active" : ""}`}
            onClick={() => toggleMode(false)}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`tab-btn ${isSignUp ? "active" : ""}`}
            onClick={() => toggleMode(true)}
          >
            Create account
          </button>
        </div>

        <h2>{isSignUp ? "Register new account" : "Caregiver login"}</h2>

        {isSignUp && (
          <div className="form-row">
            <label htmlFor="fullName">Full Name</label>
            <input
              id="fullName"
              type="text"
              placeholder="e.g. Sarah Jenkins, RN"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
        )}

        <div className="form-row">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="name@caremonitor.org"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="form-row">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <p className="error">{error}</p>}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? (isSignUp ? "Creating account…" : "Signing in…") : isSignUp ? "Sign Up" : "Sign in"}
        </button>

        {!isSignUp ? (
          <p className="hint">
            Caregiver Login: caregiver@wellbeing.care / Caregiver123!
            <br />
            <a href="#signup" onClick={(e) => { e.preventDefault(); toggleMode(true); }} className="toggle-link">
              Need an account? Create one here
            </a>
          </p>
        ) : (
          <p className="hint">
            <a href="#signin" onClick={(e) => { e.preventDefault(); toggleMode(false); }} className="toggle-link">
              Already have an account? Sign in here
            </a>
          </p>
        )}
      </form>
    </div>
  );
}
