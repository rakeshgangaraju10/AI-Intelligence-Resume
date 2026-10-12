import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAnalysis } from "../services/analyses";
import { ApiError } from "../services/api";
import { fetchCurrentUser } from "../services/auth";
import { uploadResume } from "../services/resumes";
import { renderWithProviders } from "../test/utils";
import type { AnalysisDetail } from "../types/api";
import { AnalysisDetailPage } from "./AnalysisDetailPage";
import { ResumeUploadPage } from "./ResumeUploadPage";

vi.mock("../services/auth", () => ({ fetchCurrentUser: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() }));
vi.mock("../services/resumes", () => ({ uploadResume: vi.fn() }));
vi.mock("../services/analyses", () => ({ getAnalysis: vi.fn(), deleteAnalysis: vi.fn() }));

beforeEach(() => {
  vi.mocked(fetchCurrentUser).mockResolvedValue({ id: 1, email: "a@example.com", full_name: "A", date_joined: "2026-01-01T00:00:00Z" });
});

function pdf(name = "resume.pdf", size = 2048, type = "application/pdf") {
  return new File([new Uint8Array(size)], name, { type });
}

describe("ResumeUploadPage", () => {
  it("rejects a non-PDF before uploading", async () => {
    renderWithProviders(<ResumeUploadPage />, { route: "/resumes/upload", path: "/resumes/upload" });
    fireEvent.change(screen.getByTestId("resume-file-input"), { target: { files: [pdf("resume.docx")] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Only PDF files (.pdf) can be uploaded.");
    expect(screen.getByRole("button", { name: /upload and analyze/i })).toBeDisabled();
    expect(uploadResume).not.toHaveBeenCalled();
  });

  it("explains a server-side rejection in plain language", async () => {
    vi.mocked(uploadResume).mockRejectedValue(
      new ApiError(400, "validation_error", "x", { file: [{ code: "pdf_no_text", message: "No selectable text was found." }] }),
    );
    renderWithProviders(<ResumeUploadPage />, { route: "/resumes/upload", path: "/resumes/upload" });
    fireEvent.change(screen.getByTestId("resume-file-input"), { target: { files: [pdf()] } });
    expect(screen.getByLabelText(/title/i)).toHaveValue("resume");
    await userEvent.click(screen.getByRole("button", { name: /upload and analyze/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/scanned image/i);
  });

  it("navigates to the review page after a successful upload", async () => {
    vi.mocked(uploadResume).mockResolvedValue({ id: "abc-123" } as Awaited<ReturnType<typeof uploadResume>>);
    renderWithProviders(<ResumeUploadPage />, {
      route: "/resumes/upload",
      path: "/resumes/upload",
      extraRoutes: [{ path: "/resumes/:resumeId", element: <p>Review page</p> }],
    });
    fireEvent.change(screen.getByTestId("resume-file-input"), { target: { files: [pdf()] } });
    await userEvent.click(screen.getByRole("button", { name: /upload and analyze/i }));
    expect(await screen.findByText("Review page")).toBeInTheDocument();
    expect(uploadResume).toHaveBeenCalledWith(expect.any(File), "resume", expect.any(Function));
  });
});

const ANALYSIS: AnalysisDetail = {
  id: 7,
  resume: "r-1",
  job: 3,
  resume_title: "Backend v2",
  job_title: "Backend Intern @ Acme",
  score: 58,
  score_label: "Resume-to-job matching score: … It is not a probability of being hired.",
  required_coverage: 60,
  preferred_coverage: 50,
  required_share: 0.8,
  algorithm_version: "baseline-v1",
  breakdown: {
    formula: "0.80 × required coverage (60.0) + 0.20 × preferred coverage (50.0)",
    required: { matched_weight: 3, total_weight: 5, coverage: 60 },
    preferred: { matched_weight: 1, total_weight: 2, coverage: 50 },
    required_share: 0.8,
    related_skills_count_toward_score: false,
  },
  strengths: ["Django: demonstrated in Project: Inventory Tracker"],
  improvements: ["Missing required skill: Docker"],
  suggestions: ["Docker: if you have real experience with it, add it…"],
  skill_results: [
    { skill_name: "Python", kind: "required", weight: 2, status: "matched", evidence: [{ location: "Skills section", text: "Python, SQL" }], related_to: [], related_reason: "", explanation: "Required skill 'Python' found." },
    { skill_name: "Docker", kind: "required", weight: 1, status: "missing", evidence: [], related_to: [], related_reason: "", explanation: "Required skill 'Docker' was not found in your resume." },
    { skill_name: "MySQL", kind: "required", weight: 1, status: "related", evidence: [], related_to: ["PostgreSQL"], related_reason: "relational SQL databases", explanation: "Related skills are shown for context and do not add to the score." },
    { skill_name: "React", kind: "preferred", weight: 1, status: "matched", evidence: [], related_to: [], related_reason: "", explanation: "Preferred skill 'React' found." },
  ],
  created_at: "2026-10-12T07:00:00Z",
};

describe("AnalysisDetailPage", () => {
  it("shows the score with its honest label, the formula and grouped results", async () => {
    vi.mocked(getAnalysis).mockResolvedValue(ANALYSIS);
    renderWithProviders(<AnalysisDetailPage />, { route: "/analyses/7", path: "/analyses/:analysisId" });

    expect(await screen.findByText("58.0")).toBeInTheDocument();
    expect(screen.getByText(/not a probability of being hired/i)).toBeInTheDocument();
    expect(screen.getByText(/0\.80 × required coverage/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Missing required skills (2)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Matched required skills (1)" })).toBeInTheDocument();
    expect(screen.getByText("Related skill found")).toBeInTheDocument();
    expect(screen.getByText("Missing required skill: Docker")).toBeInTheDocument();
    expect(getAnalysis).toHaveBeenCalledWith(7);
  });

  it("shows a not-found message for another user's or unknown analysis", async () => {
    vi.mocked(getAnalysis).mockRejectedValue(new ApiError(404, "not_found", "Not found."));
    renderWithProviders(<AnalysisDetailPage />, { route: "/analyses/999", path: "/analyses/:analysisId" });
    expect(await screen.findByText("Analysis not found")).toBeInTheDocument();
  });
});
