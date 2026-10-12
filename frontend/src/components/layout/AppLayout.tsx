import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router";

import { useAuth } from "../../features/auth/AuthContext";
import { Button } from "../ui/Button";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/resumes", label: "Resumes" },
  { to: "/jobs", label: "Jobs" },
  { to: "/analyses", label: "Analyses" },
  { to: "/settings", label: "Settings" },
];

function navClass({ isActive }: { isActive: boolean }): string {
  return `block rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? "bg-indigo-50 text-indigo-800" : "text-slate-700 hover:bg-slate-100"
  }`;
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
      navigate("/login");
    }
  }

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="border-b border-slate-200 bg-white print:hidden">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/dashboard" className="text-lg font-bold text-indigo-800">
            CareerForge
          </Link>
          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={navClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="hidden items-center gap-3 md:flex">
            <span className="max-w-[12rem] truncate text-sm text-slate-600" title={user?.email}>
              {user?.full_name}
            </span>
            <Button variant="secondary" size="sm" onClick={handleLogout} loading={loggingOut}>
              Log out
            </Button>
          </div>
          <button
            type="button"
            className="rounded-md p-2 text-slate-700 hover:bg-slate-100 md:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="sr-only">{menuOpen ? "Close menu" : "Open menu"}</span>
            <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {menuOpen ? <path d="M6 6l12 12M6 18L18 6" /> : <path d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>
        {menuOpen && (
          <nav id="mobile-nav" aria-label="Main" className="space-y-1 border-t border-slate-200 px-4 py-3 md:hidden">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={navClass} onClick={() => setMenuOpen(false)}>
                {item.label}
              </NavLink>
            ))}
            <Button variant="secondary" size="sm" className="mt-2 w-full" onClick={handleLogout} loading={loggingOut}>
              Log out
            </Button>
          </nav>
        )}
      </header>
      <main id="main" className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
