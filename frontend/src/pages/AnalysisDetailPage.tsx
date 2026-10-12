import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { Button, LinkButton } from "../components/ui/Button";
import { Alert, Card, PageHeader, ProgressBar } from "../components/ui/Feedback";
import { PageSpinner } from "../components/ui/Spinner";
import { SkillResultList } from "../features/analyses/SkillResultList";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDateTime, formatPercent } from "../lib/format";
import { deleteAnalysis, downloadReport, getAnalysis, saveFile } from "../services/analyses";
import { toApiError } from "../services/api";

function FeedbackList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <p className="text-sm text-slate-600">{empty}</p>
      ) : (
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function AnalysisDetailPage() {
  const analysisId = Number(useParams().analysisId);
  const navigate = useNavigate();
  const { data: a, error, loading } = useApiData(() => getAnalysis(analysisId), [analysisId]);
  useDocumentTitle(a ? `Analysis: ${a.job_title}` : "Analysis");
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (!Number.isInteger(analysisId) || error?.status === 404) {
    return (
      <Alert tone="error" title="Analysis not found">
        <Link to="/analyses" className="underline">
          Back to analyses
        </Link>
      </Alert>
    );
  }
  if (loading && !a) return <PageSpinner label="Loading analysis" />;
  if (error || !a) return <Alert tone="error">{error?.message ?? "Couldn't load this analysis."}</Alert>;

  const analysis = a;
  const by = (kind: "required" | "preferred", status: "matched" | "missing" | "related") =>
    analysis.skill_results.filter((r) => r.kind === kind && r.status === status);
  const missingRequired = [...by("required", "missing"), ...by("required", "related")];
  const missingPreferred = [...by("preferred", "missing"), ...by("preferred", "related")];

  async function handleDelete() {
    if (!window.confirm("Delete this analysis from your history?")) return;
    setDeleting(true);
    try {
      await deleteAnalysis(analysisId);
      navigate("/analyses", { replace: true });
    } catch (err) {
      setActionError(toApiError(err).message);
      setDeleting(false);
    }
  }

  async function handleDownload() {
    setDownloading(true);
    setActionError(null);
    try {
      saveFile(await downloadReport(analysisId));
    } catch (err) {
      setActionError(toApiError(err).message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={analysis.job_title}
        description={
          <>
            Resume:{" "}
            <Link to={`/resumes/${analysis.resume}`} className="text-indigo-700 underline">
              {analysis.resume_title}
            </Link>{" "}
            · analysed {formatDateTime(analysis.created_at)}
          </>
        }
        actions={
          <div className="flex flex-wrap gap-2 print:hidden">
            <LinkButton to={`/jobs/${analysis.job}?resume=${analysis.resume}`} variant="secondary">
              Re-run with edits
            </LinkButton>
            <Button variant="secondary" onClick={handleDownload} loading={downloading}>
              Download report
            </Button>
            <Button variant="secondary" onClick={() => window.print()}>
              Print
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              Delete
            </Button>
          </div>
        }
      />
      {actionError && <Alert tone="error">{actionError}</Alert>}

      <Card>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="text-center md:border-r md:border-slate-100 md:pr-6">
            <p className="text-sm font-medium text-slate-600">Resume-to-job matching score</p>
            <p className="mt-1 text-5xl font-bold text-slate-900">
              {analysis.score.toFixed(1)}
              <span className="text-xl font-medium text-slate-500"> / 100</span>
            </p>
            <p className="mt-2 text-xs text-slate-500">{analysis.score_label}</p>
          </div>
          <div className="space-y-4 md:col-span-2">
            <div>
              <div className="mb-1 flex justify-between gap-2 text-sm">
                <span className="font-medium text-slate-800">Required skills</span>
                <span className="text-slate-600">
                  {formatPercent(analysis.required_coverage)} ({analysis.breakdown.required.matched_weight}/
                  {analysis.breakdown.required.total_weight} weight)
                </span>
              </div>
              <ProgressBar value={analysis.required_coverage ?? 0} label="Required skill coverage" />
            </div>
            <div>
              <div className="mb-1 flex justify-between gap-2 text-sm">
                <span className="font-medium text-slate-800">Preferred skills</span>
                <span className="text-slate-600">
                  {formatPercent(analysis.preferred_coverage)} ({analysis.breakdown.preferred.matched_weight}/
                  {analysis.breakdown.preferred.total_weight} weight)
                </span>
              </div>
              <ProgressBar value={analysis.preferred_coverage ?? 0} label="Preferred skill coverage" />
            </div>
            <p className="hidden text-sm text-slate-700 print:block">Score = {analysis.breakdown.formula}</p>
            <details className="text-sm print:hidden">
              <summary className="cursor-pointer font-medium text-indigo-700">How this score was calculated</summary>
              <div className="mt-2 space-y-1 text-slate-700">
                <p>
                  Score = <code className="rounded bg-slate-100 px-1">{analysis.breakdown.formula}</code>
                </p>
                <p>
                  Coverage is the weighted share of the job's skills found in your resume. Related skills are shown for context
                  but don't count toward the score. Algorithm version: {analysis.algorithm_version}.
                </p>
              </div>
            </details>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={`Missing required skills (${missingRequired.length})`}>
          <SkillResultList results={missingRequired} emptyText="Every required skill was found in your resume." />
        </Card>
        <Card title={`Matched required skills (${by("required", "matched").length})`}>
          <SkillResultList results={by("required", "matched")} emptyText="None of the required skills were found." />
        </Card>
        <Card title={`Missing preferred skills (${missingPreferred.length})`}>
          <SkillResultList results={missingPreferred} emptyText="No preferred skills are missing." />
        </Card>
        <Card title={`Matched preferred skills (${by("preferred", "matched").length})`}>
          <SkillResultList results={by("preferred", "matched")} emptyText="No preferred skills matched (or the job lists none)." />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <FeedbackList
          title="Strengths"
          items={analysis.strengths}
          empty="No skills with usage evidence yet. Show where you used your skills in projects or experience."
        />
        <FeedbackList title="Areas for improvement" items={analysis.improvements} empty="Nothing to flag." />
        <FeedbackList title="Suggestions" items={analysis.suggestions} empty="No suggestions." />
      </div>
    </div>
  );
}
