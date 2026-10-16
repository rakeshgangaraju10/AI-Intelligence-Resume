import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SAMPLE_JOBS } from "../lib/sampleJobs";
import { fetchCurrentUser } from "../services/auth";
import { createJob } from "../services/jobs";
import { renderWithProviders } from "../test/utils";
import { JobNewPage } from "./JobNewPage";

vi.mock("../services/auth", () => ({ fetchCurrentUser: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() }));
vi.mock("../services/jobs", () => ({ createJob: vi.fn() }));

beforeEach(() => {
  vi.mocked(fetchCurrentUser).mockResolvedValue({ id: 1, email: "a@example.com", full_name: "A", date_joined: "2026-01-01T00:00:00Z" });
  vi.mocked(createJob).mockResolvedValue({ id: 42 } as Awaited<ReturnType<typeof createJob>>);
});

const routes = { path: "/jobs/new", extraRoutes: [{ path: "/jobs/:jobId", element: <p>Job page</p> }] };

describe("Sample jobs", () => {
  it("offers every sample and fills the form with one click", async () => {
    renderWithProviders(<JobNewPage />, { route: "/jobs/new", ...routes });
    for (const sample of SAMPLE_JOBS) {
      expect(await screen.findByRole("button", { name: sample.title })).toBeInTheDocument();
    }
    await userEvent.click(screen.getByRole("button", { name: "Data Analyst (Fresher)" }));
    expect(screen.getByLabelText(/^job title/i)).toHaveValue("Data Analyst (Fresher)");
    expect(screen.getByRole("status")).toHaveTextContent("Filled in “Data Analyst (Fresher)”");

    await userEvent.click(screen.getByRole("button", { name: "Save job" }));
    expect(await screen.findByText("Job page")).toBeInTheDocument();
    expect(createJob).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Data Analyst (Fresher)",
        company: "Sample job (example)",
        experience_level: "entry",
        required_skills: ["SQL", "Microsoft Excel", "Python", "Pandas", "Data Analysis"],
        preferred_skills: ["Power BI", "Tableau", "Matplotlib"],
        auto_extract: false,
      }),
    );
  });

  it("prefills from ?sample= (used by the empty Jobs page)", async () => {
    renderWithProviders(<JobNewPage />, { route: "/jobs/new?sample=python-developer", ...routes });
    expect(await screen.findByLabelText(/^job title/i)).toHaveValue("Junior Python Developer");
    expect(screen.getByLabelText(/^required skills/i)).toHaveValue(
      "Python, Django, Django REST Framework, PostgreSQL, SQL, REST APIs, Git",
    );
  });

  it("ignores an unknown sample id", async () => {
    renderWithProviders(<JobNewPage />, { route: "/jobs/new?sample=nope", ...routes });
    expect(await screen.findByLabelText(/^job title/i)).toHaveValue("");
  });

  it("samples are clearly marked as examples and use unique ids", () => {
    const ids = new Set(SAMPLE_JOBS.map((s) => s.id));
    expect(ids.size).toBe(SAMPLE_JOBS.length);
    for (const sample of SAMPLE_JOBS) {
      expect(sample.company).toMatch(/example/i);
      expect(sample.description).toMatch(/example posting/i);
      expect(sample.required_skills.length).toBeGreaterThan(0);
    }
  });
});
