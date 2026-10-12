import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AuthProvider } from "../features/auth/AuthContext";

interface Options {
  /** Initial URL, e.g. "/resumes/abc". */
  route?: string;
  /** Route pattern the element is mounted on, e.g. "/resumes/:resumeId". */
  path?: string;
  /** Extra routes so navigation targets render something assertable. */
  extraRoutes?: { path: string; element: ReactElement }[];
}

export function renderWithProviders(ui: ReactElement, { route = "/", path = "/", extraRoutes = [] }: Options = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>
        <Routes>
          <Route path={path} element={ui} />
          {extraRoutes.map((r) => (
            <Route key={r.path} path={r.path} element={r.element} />
          ))}
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}
