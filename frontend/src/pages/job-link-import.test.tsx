import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/api";
import { fetchCurrentUser } from "../services/auth";
import { createJob, importJobFromUrl } from "../services/jobs";
import { renderWithProviders } from "../test/utils";
import { JobNewPage } from "./JobNewPage";

vi.mock("../services/auth", () => ({ fetchCurrentUser: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() }));
vi.mock("../services/jobs", () => ({ createJob: vi.fn(), importJobFromUrl: vi.fn() }));

const routes = { route: "/jobs/new", path: "/jobs/new", extraRoutes: [{ path: "/jobs/:jobId", element: <p>Job page</p> }] };
const LINK = "https://boards.greenhouse.io/acme/jobs/123";

beforeEach(() => {
  vi.mocked(fetchCurrentUser).mockResolvedValue({ id: 1, email: "a@example.com", full_name: "A", college_name: "Example College", graduation_year: 2025, date_joined: "2026-01-01T00:00:00Z" });
  vi.mocked(createJob).mockResolvedValue({ id: 7 } as Awaited<ReturnType<typeof createJob>>);
});

async function importLink(link = LINK) {
  await userEvent.type(await screen.findByLabelText(/job posting link/i), link);
  await userEvent.click(screen.getByRole("button", { name: "Import job" }));
}

describe("Import a job from a link", () => {
  it("fills the form from the link, then saves with skill suggestions on", async () => {
    vi.mocked(importJobFromUrl).mockResolvedValue({
      title: "Junior Backend Developer",
      company: "Acme Example",
      description: `Source: ${LINK}\n\nRequirements\n- Python\n- Django`,
      source_url: LINK,
      method: "structured",
      warnings: [],
    });
    renderWithProviders(<JobNewPage />, routes);
    await importLink();

    expect(await screen.findByText(/Imported “Junior Backend Developer” from boards.greenhouse.io/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^job title/i)).toHaveValue("Junior Backend Developer");
    expect(screen.getByLabelText(/^company/i)).toHaveValue("Acme Example");
    expect(screen.getByLabelText(/^job description/i)).toHaveValue(`Source: ${LINK}\n\nRequirements\n- Python\n- Django`);
    expect(screen.getByLabelText(/suggest skills from the description/i)).toBeChecked();
    expect(importJobFromUrl).toHaveBeenCalledWith(LINK);

    await userEvent.click(screen.getByRole("button", { name: "Save job" }));
    expect(await screen.findByText("Job page")).toBeInTheDocument();
    expect(createJob).toHaveBeenCalledWith(expect.objectContaining({ title: "Junior Backend Developer", auto_extract: true }));
  });

  it("shows the page-text warning so the user tidies the description", async () => {
    vi.mocked(importJobFromUrl).mockResolvedValue({
      title: "Python Developer", company: "", description: "Source: x\n\ntext", source_url: "https://careers.example.com/1",
      method: "page_text", warnings: ["This page has no structured job data, so all of its text was imported."],
    });
    renderWithProviders(<JobNewPage />, routes);
    await importLink("https://careers.example.com/1");
    expect(await screen.findByText(/no structured job data/)).toBeInTheDocument();
  });

  it("explains sites that can't be imported", async () => {
    vi.mocked(importJobFromUrl).mockRejectedValue(
      new ApiError(400, "validation_error", "x", {
        url: [{ code: "unsupported_site", message: "LinkedIn doesn't allow job pages to be read automatically." }],
      }),
    );
    renderWithProviders(<JobNewPage />, routes);
    await importLink("https://www.linkedin.com/jobs/view/1");
    expect(await screen.findByRole("alert")).toHaveTextContent("LinkedIn doesn't allow");
    expect(screen.getByLabelText(/^job title/i)).toHaveValue("");
  });

  it("checks the link looks like a URL before calling the server", async () => {
    renderWithProviders(<JobNewPage />, routes);
    await importLink("careers dot example");
    expect(await screen.findByRole("alert")).toHaveTextContent("starting with https://");
    expect(importJobFromUrl).not.toHaveBeenCalled();
  });
});
