import { Link, Outlet } from "react-router";

import { useAuth } from "../../features/auth/AuthContext";
import { LinkButton } from "../ui/Button";
import { DemoBanner } from "./DemoBanner";

export function PublicLayout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-screen flex-col">
      <DemoBanner />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold text-indigo-800">
            CareerForge
          </Link>
          <nav aria-label="Account" className="flex items-center gap-2">
            {user ? (
              <LinkButton to="/dashboard" size="sm">
                Go to dashboard
              </LinkButton>
            ) : (
              <>
                <LinkButton to="/login" variant="ghost" size="sm">
                  Log in
                </LinkButton>
                <LinkButton to="/register" size="sm">
                  Create account
                </LinkButton>
              </>
            )}
          </nav>
        </div>
      </header>
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        CareerForge: an explainable resume-to-job matching tool. Scores describe skill overlap, not hiring chances.
      </footer>
    </div>
  );
}
