import axios from "axios";

export const AUTH_EXPIRED_EVENT = "ewm:auth-expired";

const DEFAULT_TIMEOUT_MS = 15_000;
const PREDICTION_TIMEOUT_MS = 120_000;
const configuredBaseUrl = (
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || ""
).trim().replace(/\/+$/, "");

// An empty base URL intentionally keeps API calls on the frontend origin so
// Vite's /api proxy is used during local development.
const api = axios.create({
  baseURL: configuredBaseUrl || "",
  timeout: DEFAULT_TIMEOUT_MS,
});

export function isUnauthorized(error) {
  return error?.response?.status === 401;
}

export function getApiError(error, fallback = "Request failed.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;

  if (error?.code === "ECONNABORTED" || error?.code === "ETIMEDOUT") {
    return "The request timed out. Make sure the backend is running, then try again.";
  }

  if (error?.request && !error?.response) {
    return "Cannot reach the backend. Start the local services and try again.";
  }

  if (isUnauthorized(error)) {
    return "Your caregiver session has expired. Please sign in again.";
  }

  return error?.message || fallback;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ewm_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const hasSession = Boolean(localStorage.getItem("ewm_token"));
    if (isUnauthorized(error) && hasSession && !error.config?.skipAuthExpiry) {
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  }
);

export async function login(email, password) {
  const { data } = await api.post(
    "/api/auth/login/json",
    { email, password },
    { skipAuthExpiry: true }
  );
  return data;
}

export async function register(email, fullName, password) {
  const { data } = await api.post(
    "/api/auth/register",
    {
      email,
      full_name: fullName,
      password,
    },
    { skipAuthExpiry: true }
  );
  return data;
}

export async function logout() {
  await api.post("/api/auth/logout", undefined, { skipAuthExpiry: true });
}

export async function getMe() {
  const { data } = await api.get("/api/auth/me");
  return data;
}

export async function getDashboard() {
  const { data } = await api.get("/api/dashboard/stats");
  return data;
}

export async function listElderly() {
  const { data } = await api.get("/api/elderly");
  return data;
}

export async function createElderly(payload) {
  const { data } = await api.post("/api/elderly", payload);
  return data;
}

export async function startSession(elderlyId) {
  const { data } = await api.post("/api/monitoring/sessions/start", { elderly_id: elderlyId });
  return data;
}

export async function stopSession(sessionId) {
  const { data } = await api.post(`/api/monitoring/sessions/${sessionId}/stop`);
  return data;
}

function absoluteApiUrl(path) {
  if (typeof window === "undefined") return path;
  const base = configuredBaseUrl || window.location.origin;
  return new URL(path, base).toString();
}

// pagehide/unmount cannot reliably await Axios. A keepalive fetch gives the
// backend a best-effort opportunity to close the active monitoring session.
export function stopSessionKeepalive(sessionId) {
  if (!sessionId || typeof window === "undefined" || typeof window.fetch !== "function") {
    return;
  }

  const token = localStorage.getItem("ewm_token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  void window.fetch(absoluteApiUrl(`/api/monitoring/sessions/${sessionId}/stop`), {
    method: "POST",
    headers,
    keepalive: true,
  }).catch(() => {
    // Navigation is already in progress; normal startup recovery handles any
    // session the browser could not close.
  });
}

export async function predictExpression(imageBase64, sessionId) {
  const { data } = await api.post(
    "/api/monitoring/predict",
    {
      image_base64: imageBase64,
      session_id: sessionId,
    },
    { timeout: PREDICTION_TIMEOUT_MS }
  );
  return data;
}

export async function saveObservation(payload) {
  const { data } = await api.post("/api/monitoring/observations", payload);
  return data;
}

export async function listObservations(params = {}) {
  const { data } = await api.get("/api/monitoring/observations", { params });
  return data;
}

export async function getAnalytics() {
  const { data } = await api.get("/api/analytics");
  return data;
}

export async function listReports() {
  const { data } = await api.get("/api/reports");
  return data;
}

export async function createReport(payload) {
  const { data } = await api.post("/api/reports", payload);
  return data;
}

export async function exportReport(reportId) {
  const { data } = await api.get(`/api/reports/${reportId}/export`);
  return data;
}

export default api;
