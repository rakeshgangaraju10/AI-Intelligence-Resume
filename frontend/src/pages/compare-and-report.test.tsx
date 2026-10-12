import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { compareAnalyses, downloadReport, getAnalysis, listAnalyses, saveFile } from "../services/analyses";
import { ApiError } from "../services/api";
import { fetchCurrentUser } from "../services/auth";
import { listResumes } from "../services/resumes";
import { renderWithProviders } from "../test/utils";
import type { AnalysisComparison, AnalysisDetail, AnalysisListItem } from "../types/api";
import { AnalysesPage } from "./AnalysesPage";
import { AnalysisComparePage } from "./AnalysisComparePage";
import { AnalysisDetailPage } from "./AnalysisDetailPage";

vi.mock("../services/auth", () => ({ fetchCurrentUser: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() }));
vi.mock("../services/resumes", () => ({ listResumes: vi.fn() }));
vi.mock("../services/analyses", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/analyses")>();
  return {
    filenameFromDisposition: actual.filenameFromDisposition,
    listAnalyses: vi.fn(),
    getAnalysis: vi.fn(),
    deleteAnalysis: vi.fn(),
    compareAnalyses: vi.fn(),
    downloadReport: vi.fn(),
    saveFile: vi.fn(),
  };
});

beforeEach(() => {
  vi.mocked(fetchCurrentUser).mockResolvedValue({ id: 1, email: "a@example.com", full_name: "A", date_joined: "2026-01-01T00:00:00Z" });
  vi.mocked(listResumes).mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
});

function item(id: number, score: number): AnalysisListItem {
  return {
    id, resume: "r-1", job: 3, resume_title: "Backend v" + id, job_title: "Backend Intern", score,
    required_coverage: score, preferred_coverage: null, matched_count: 2, missing_count: 1,
    algorithm_version: "baseline-v1", created_at: `2026-10-0${id}T07:00:00Z`,
  };
}

function detail(id: number, score: number): AnalysisDetail {
  return {
    id, resume: "r-1", job: 3, resume_title: "Backend v" + id, job_title: "Backend Intern", score,
    score_label: "Not a probability of being hired.", required_coverage: score, preferred_coverage: null,
    required_share: 0.8, algorithm_version: "baseline-v1",
    breakdown: {
      formula: "0.80 × required coverage", required: { matched_weight: 1, total_weight: 2, coverage: score },
      preferred: { matched_weight: 0, total_weight: 0, coverage: null }, required_share: 0.8,
      related_skills_count_toward_score: false,
    },
    strengths: [], improvements: [], suggestions: [], skill_results: [], created_at: "2026-10-12T07:00:00Z",
  };
}

function LocationProbe() {
  const location = useLocation();
  return <p>At {location.pathname + location.search}</p>;
}

describe("AnalysesPage comparison selection", () => {
  it("allows exactly two selections and opens the comparison, older first", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ count: 3, next: null, previous: null, results: [item(9, 74), item(5, 58), item(2, 40)] });
    renderWithProviders(<AnalysesPage />, {
      route: "/analyses",
      path: "/analyses",
      extraRoutes: [{ path: "/analyses/compare", element: <LocationProbe /> }],
    });
    const boxes = await screen.findAllByRole("checkbox", { name: /for comparison/i });
    const compare = screen.getByRole("button", { name: "Compare selected" });
    expect(compare).toBeDisabled();

    await userEvent.click(boxes[0]);
    await userEvent.click(boxes[1]);
    expect(boxes[2]).toBeDisabled();
    expect(screen.getByText("2 analyses selected")).toBeInTheDocument();

    await userEvent.click(compare);
    expect(await screen.findByText("At /analyses/compare?a=5&b=9")).toBeInTheDocument();
  });
});

const COMPARISON: AnalysisComparison = {
  a: detail(5, 58),
  b: detail(9, 74),
  score_delta: 16,
  basis: "same_resume_and_job",
  skills: [
    { skill_name: "Docker", kind_a: "required", kind_b: "required", status_a: "missing", status_b: "matched", change: "gained" },
    { skill_name: "Python", kind_a: "required", kind_b: "required", status_a: "matched", status_b: "matched", change: "unchanged" },
  ],
};

describe("AnalysisComparePage", () => {
  it("shows the score change and per-skill changes", async () => {
    vi.mocked(compareAnalyses).mockResolvedValue(COMPARISON);
    renderWithProviders(<AnalysisComparePage />, { route: "/analyses/compare?a=5&b=9", path: "/analyses/compare" });
    expect(await screen.findByText("+16.0")).toBeInTheDocument();
    expect(screen.getByText(/58\.0 → 74\.0/)).toBeInTheDocument();
    expect(screen.getByText(/not a hiring probability/i)).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Docker/ })).toHaveTextContent("Gained");
    expect(screen.getByText("1 of 2 skills changed")).toBeInTheDocument();
    expect(compareAnalyses).toHaveBeenCalledWith(5, 9);
  });

  it("warns when the analyses are against different jobs", async () => {
    vi.mocked(compareAnalyses).mockResolvedValue({ ...COMPARISON, basis: "same_resume", score_delta: -12.5 });
    renderWithProviders(<AnalysisComparePage />, { route: "/analyses/compare?a=5&b=9", path: "/analyses/compare" });
    expect(await screen.findByText("−12.5")).toBeInTheDocument();
    expect(screen.getByText(/not an improvement or a decline/i)).toBeInTheDocument();
  });

  it("rejects missing or identical ids without calling the API", async () => {
    renderWithProviders(<AnalysisComparePage />, { route: "/analyses/compare?a=5&b=5", path: "/analyses/compare" });
    expect(await screen.findByText("Choose two analyses")).toBeInTheDocument();
    expect(compareAnalyses).not.toHaveBeenCalled();
  });

  it("shows not found for another user's analysis", async () => {
    vi.mocked(compareAnalyses).mockRejectedValue(new ApiError(404, "not_found", "Analysis not found."));
    renderWithProviders(<AnalysisComparePage />, { route: "/analyses/compare?a=5&b=999", path: "/analyses/compare" });
    expect(await screen.findByText("Analysis not found")).toBeInTheDocument();
  });
});

describe("AnalysisDetailPage report actions", () => {
  it("downloads the Markdown report", async () => {
    vi.mocked(getAnalysis).mockResolvedValue(detail(7, 58));
    const file = { blob: new Blob(["# report"], { type: "text/markdown" }), filename: "careerforge-analysis-7.md" };
    vi.mocked(downloadReport).mockResolvedValue(file);
    renderWithProviders(<AnalysisDetailPage />, { route: "/analyses/7", path: "/analyses/:analysisId" });
    await userEvent.click(await screen.findByRole("button", { name: "Download report" }));
    expect(downloadReport).toHaveBeenCalledWith(7);
    expect(saveFile).toHaveBeenCalledWith(file);
  });

  it("shows an error if the download fails", async () => {
    vi.mocked(getAnalysis).mockResolvedValue(detail(7, 58));
    vi.mocked(downloadReport).mockRejectedValue(new ApiError(500, "server_error", "Something went wrong on our side."));
    renderWithProviders(<AnalysisDetailPage />, { route: "/analyses/7", path: "/analyses/:analysisId" });
    await userEvent.click(await screen.findByRole("button", { name: "Download report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side.");
  });

  it("prints with the browser's print dialog", async () => {
    vi.mocked(getAnalysis).mockResolvedValue(detail(7, 58));
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    renderWithProviders(<AnalysisDetailPage />, { route: "/analyses/7", path: "/analyses/:analysisId" });
    await userEvent.click(await screen.findByRole("button", { name: "Print" }));
    expect(print).toHaveBeenCalled();
  });
});
