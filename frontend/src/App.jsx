import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const LiveMonitoringPage = lazy(() => import("./pages/LiveMonitoringPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const ProfilesPage = lazy(() => import("./pages/ProfilesPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));

export default function App() {
  const { token } = useAuth();

  return (
    <Suspense fallback={<p>Loading application…</p>}>
      <Routes>
        <Route path="/login" element={token ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="profiles" element={<ProfilesPage />} />
          <Route path="live" element={<LiveMonitoringPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
      </Routes>
    </Suspense>
  );
}
