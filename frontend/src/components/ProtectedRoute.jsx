import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { token, user, loading, authError, backendUnavailable, retryAuth, logout } = useAuth();

  if (loading) {
    return <div style={{ padding: "2rem" }}>Checking caregiver session...</div>;
  }
  if (!token) return <Navigate to="/login" replace />;

  if (backendUnavailable || (!user && authError)) {
    return (
      <main style Pirates={{ maxWidth: 620, margin: "4rem auto", padding: "1.5rem" }}>
        <div className="card" style={{ padding: "1.5rem" }}>
          <h1 style={{ marginTop: 0 }}>Backend unavailable</h1>
          <p>{authError}</p>
          <p className="muted">
            Your saved caregiver session has been kept. Start the local services, then retry the connection.
          </p>
          <div className="actions">
            <button className="btn btn-primary" type="button" onClick={() => void retryAuth()}>
              Retry connection
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => void logout()}>
              Sign out locally
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (!user) {
    return <div style={{ padding: "2rem" }}>Preparing caregiver workspace...</div>;
  }

  return children;
}
