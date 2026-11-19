import { Suspense, lazy } from "react";
import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { Loading } from "./components/ui";
import { AppShell } from "./layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage, ForbiddenPage } from "./pages/NotFoundPage";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const RisksPage = lazy(() => import("./pages/RisksPage"));
const RiskDetailPage = lazy(() => import("./pages/RiskDetailPage"));
const RiskFormPage = lazy(() => import("./pages/RiskFormPage"));
const ActionsPage = lazy(() => import("./pages/ActionsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const AssetsPage = lazy(() => import("./pages/AssetsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const ImportsPage = lazy(() => import("./pages/ImportsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const KitchenSinkPage = lazy(() => import("./pages/KitchenSinkPage"));

function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Loading label="Checking your session…" />;
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <>{children}</>;
}

/** Route guard by permission; the API refuses the same requests regardless (403). */
function Allow({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth();
  return can(permission) ? <>{children}</> : <ForbiddenPage />;
}

export function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/kitchen-sink" element={<KitchenSinkPage />} />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="risks" element={<RisksPage />} />
          <Route
            path="risks/new"
            element={
              <Allow permission="create_risk">
                <RiskFormPage />
              </Allow>
            }
          />
          <Route path="risks/:code" element={<RiskDetailPage />} />
          <Route path="risks/:code/edit" element={<RiskFormPage />} />
          <Route path="actions" element={<ActionsPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route
            path="reports"
            element={
              <Allow permission="export_reports">
                <ReportsPage />
              </Allow>
            }
          />
          <Route
            path="imports"
            element={
              <Allow permission="import_csv">
                <ImportsPage />
              </Allow>
            }
          />
          <Route
            path="audit"
            element={
              <Allow permission="view_audit">
                <AuditPage />
              </Allow>
            }
          />
          <Route
            path="users"
            element={
              <Allow permission="manage_users">
                <UsersPage />
              </Allow>
            }
          />
          <Route
            path="settings"
            element={
              <Allow permission="manage_settings">
                <SettingsPage />
              </Allow>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
