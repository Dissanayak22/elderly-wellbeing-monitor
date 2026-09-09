import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import * as api from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("ewm_token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem("ewm_token")));
  const [authError, setAuthError] = useState("");
  const bootstrapStartedRef = useRef(false);

  const clearSession = useCallback(() => {
    localStorage.removeItem("ewm_token");
    setToken(null);
    setUser(null);
    setAuthError("");
    setLoading(false);
  }, []);

  const verifyToken = useCallback(
    async (candidateToken = localStorage.getItem("ewm_token")) => {
      if (!candidateToken) {
        clearSession();
        return { ok: false, reason: "missing" };
      }

      setLoading(true);
      setAuthError("");
      try {
        const me = await api.getMe();
        if (localStorage.getItem("ewm_token") !== candidateToken) {
          return { ok: false, reason: "stale" };
        }
        setToken(candidateToken);
        setUser(me);
        return { ok: true };
      } catch (requestError) {
        if (localStorage.getItem("ewm_token") !== candidateToken) {
          return { ok: false, reason: "stale" };
        }

        if (api.isUnauthorized(requestError)) {
          clearSession();
          return { ok: false, reason: "unauthorized" };
        }

        // A network outage does not prove that the stored JWT is invalid.
        setToken(candidateToken);
        setAuthError(api.getApiError(requestError, "Cannot verify the caregiver session."));
        return { ok: false, reason: "network" };
      } finally {
        if (localStorage.getItem("ewm_token") === candidateToken) {
          setLoading(false);
        }
      }
    },
    [clearSession]
  );

  useEffect(() => {
    if (bootstrapStartedRef.current) return;
    bootstrapStartedRef.current = true;
    const storedToken = localStorage.getItem("ewm_token");
    if (storedToken) {
      void verifyToken(storedToken);
    } else {
      setLoading(false);
    }
  }, [verifyToken]);

  useEffect(() => {
    const handleExpiredSession = () => clearSession();
    window.addEventListener(api.AUTH_EXPIRED_EVENT, handleExpiredSession);
    return () => window.removeEventListener(api.AUTH_EXPIRED_EVENT, handleExpiredSession);
  }, [clearSession]);

  const completeAuthentication = useCallback(
    async (authRequest) => {
      const data = await authRequest;
      const nextToken = data.access_token;
      localStorage.setItem("ewm_token", nextToken);
      setToken(nextToken);
      setUser(null);
      setAuthError("");

      // Verify exactly once here. The bootstrap effect does not depend on
      // token changes, so login and registration cannot issue duplicate /me calls.
      const verification = await verifyToken(nextToken);
      if (verification.reason === "unauthorized") {
        throw new Error("The new caregiver session could not be verified. Please sign in again.");
      }
      return data;
    },
    [verifyToken]
  );

  const login = useCallback(
    (email, password) => completeAuthentication(api.login(email, password)),
    [completeAuthentication]
  );

  const register = useCallback(
    (email, fullName, password) => completeAuthentication(api.register(email, fullName, password)),
    [completeAuthentication]
  );

  const retryAuth = useCallback(
    () => verifyToken(token || localStorage.getItem("ewm_token")),
    [token, verifyToken]
  );

  const logout = useCallback(async () => {
    try {
      if (localStorage.getItem("ewm_token")) await api.logout();
    } catch {
      // Local logout must still succeed if the API is down.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      authError,
      backendUnavailable: Boolean(token && authError && !user),
      login,
      register,
      logout,
      retryAuth,
    }),
    [authError, loading, login, logout, register, retryAuth, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
