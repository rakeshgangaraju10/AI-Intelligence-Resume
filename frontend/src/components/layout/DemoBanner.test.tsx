import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DemoBanner } from "./DemoBanner";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("DemoBanner", () => {
  it("is hidden in normal builds", () => {
    vi.stubEnv("VITE_DEMO_MODE", "");
    render(<DemoBanner />);
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("warns visitors on the public demo", () => {
    vi.stubEnv("VITE_DEMO_MODE", "true");
    render(<DemoBanner />);
    expect(screen.getByRole("note")).toHaveTextContent(/sample resume, not your real one/i);
  });
});
