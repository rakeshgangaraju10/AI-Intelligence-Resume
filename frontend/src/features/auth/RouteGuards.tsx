import { Navigate, Outlet, useLocation } from "react-router";

import { PageSpinner } from "../../components/ui/Spinner";
import { useAuth } from "./AuthContext";

/** Only for signed-in users; others go to /login and come back afterwards. */
export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageSpinner label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <Outlet />;
}

/** Login/register pages: signed-in users are sent to the dashboard. */
export function PublicOnlyRoute() {
  const { user, loading } = useAuth();
  if (loading) return <PageSpinner label="Checking your session" />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
