import { Link, useSearchParams } from "react-router";

import { Alert, Badge, Card, PageHeader } from "../components/ui/Feedback";
import { PageSpinner } from "../components/ui/Spinner";
import { ScoreBadge } from "../features/analyses/ScoreBadge";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDateTime, formatPercent } from "../lib/format";
import { compareAnalyses } from "../services/analyses";
import type { AnalysisDetail, ComparisonBasis, ComparisonChange, SkillResultStatus } from "../types/api";

const CHANGE_LABELS: Record<ComparisonChange, { label: string; tone: "green" | "red" | "sky" | "slate" }> = {
  gained: { label: "Gained", tone: "green" },
  lost: { label: "Lost", tone: "red" },
  only_in_a: { label: "Only in A's job", tone: "sky" },
  only_in_b: { label: "Only in B's job", tone: "sky" },
  unchanged: { label: "No change", tone: "slate" },
};

const STATUS_LABELS: Record<SkillResultStatus, string> = {
  matched: "Matched",
  missing: "Missing",
  related: "Related only",
};

const BASIS_NOTES: Record<ComparisonBasis, { text: string; warn: boolean }> = {
  same_resume_and_job: { text: "Same resume and job, analysed at different times (the resume or job may have been edited in between).", warn: false },
  same_job: { text: "Same job, different resumes: a like-for-like comparison.", warn: false },
  same_resume: { text: "Same resume against two different jobs. The scores measure different requirement lists, so the difference is not an improvement or a decline.", warn: true },
  different: { text: "Different resumes and different jobs. The scores aren't directly comparable.", warn: true },
};

function parseId(value: string | null): number | null {
  const n = Number(value);
  return value && Number.isInteger(n) && n > 0 ? n : null;
}

function formatDelta(delta: number): string {
  if (delta === 0) return "±0.0";
  return `${delta > 0 ? "+" : "−"}${Math.abs(delta).toFixed(1)}`;
}

function Side({ label, analysis }: { label: string; analysis: AnalysisDetail }) {
  return (
    <Card title={`${label}: ${analysis.job_title}`}>
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-2">
          <dt className="text-slate-600">Resume</dt>
          <dd className="min-w-0 text-right font-medium text-slate-900">{analysis.resume_title}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-600">Analysed</dt>
          <dd className="text-right text-slate-900">{formatDateTime(analysis.created_at)}</dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-slate-600">Score</dt>
          <dd>
            <ScoreBadge score={analysis.score} />
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-600">Required coverage</dt>
          <dd className="text-slate-900">{formatPercent(analysis.required_coverage)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-600">Preferred coverage</dt>
          <dd className="text-slate-900">{formatPercent(analysis.preferred_coverage)}</dd>
        </div>
      </dl>
      <Link to={`/analyses/${analysis.id}`} className="mt-3 inline-block text-sm text-indigo-700 underline">
        Open full analysis
      </Link>
    </Card>
  );
}

export function AnalysisComparePage() {
  useDocumentTitle("Compare analyses");
  const [params] = useSearchParams();
  const a = parseId(params.get("a"));
  const b = parseId(params.get("b"));
  const valid = a !== null && b !== null && a !== b;
  const { data, error, loading } = useApiData(
    () => (a !== null && b !== null && a !== b ? compareAnalyses(a, b) : Promise.resolve(null)),
    [a, b],
  );

  if (!valid) {
    return (
      <Alert tone="error" title="Choose two analyses">
        <Link to="/analyses" className="underline">
          Select two different analyses in your history
        </Link>{" "}
        to compare them.
      </Alert>
    );
  }
  if (error?.status === 404) {
    return (
      <Alert tone="error" title="Analysis not found">
        One of these analyses doesn't exist or was deleted.{" "}
        <Link to="/analyses" className="underline">
          Back to analyses
        </Link>
      </Alert>
    );
  }
  if (loading && !data) return <PageSpinner label="Comparing analyses" />;
  if (error || !data) return <Alert tone="error">{error?.message ?? "Couldn't load the comparison."}</Alert>;

  const basis = BASIS_NOTES[data.basis];
  const changed = data.skills.filter((s) => s.change !== "unchanged").length;

  return (
    <div className="space-y-6">
      <PageHeader title="Compare analyses" description="A is the earlier analysis; B is compared against it." />

      <Alert tone={basis.warn ? "warning" : "info"}>{basis.text}</Alert>

      <div className="grid gap-6 md:grid-cols-3">
        <Side label="A" analysis={data.a} />
        <Card title="Score change">
          <p className="text-center text-4xl font-bold text-slate-900" aria-label={`Score change ${formatDelta(data.score_delta)} points`}>
            {formatDelta(data.score_delta)}
          </p>
          <p className="mt-2 text-center text-sm text-slate-600">
            {data.a.score.toFixed(1)} → {data.b.score.toFixed(1)} (matching score points, not a hiring probability)
          </p>
          <p className="mt-2 text-center text-sm text-slate-600">
            {changed} of {data.skills.length} skills changed
          </p>
        </Card>
        <Side label="B" analysis={data.b} />
      </div>

      <Card title="Skill by skill">
        <div className="md:overflow-x-auto">
          <table className="block w-full text-left text-sm md:table">
            <thead className="sr-only text-xs uppercase text-slate-500 md:not-sr-only md:table-header-group">
              <tr>
                <th scope="col" className="py-2 pr-4 font-medium">Skill</th>
                <th scope="col" className="py-2 pr-4 font-medium">A</th>
                <th scope="col" className="py-2 pr-4 font-medium">B</th>
                <th scope="col" className="py-2 font-medium">Change</th>
              </tr>
            </thead>
            <tbody className="block divide-y divide-slate-100 md:table-row-group">
              {data.skills.map((s) => {
                const change = CHANGE_LABELS[s.change];
                return (
                  <tr key={s.skill_name} className="relative block py-3 md:table-row md:py-0">
                    <th scope="row" className="block pr-28 font-medium text-slate-900 md:table-cell md:py-2 md:pr-4">
                      {s.skill_name}
                    </th>
                    <td data-label="A:" className="block text-slate-700 md:table-cell md:py-2 md:pr-4 before:mr-1 before:text-xs before:font-medium before:text-slate-500 before:content-[attr(data-label)] md:before:content-none">
                      {s.status_a ? `${STATUS_LABELS[s.status_a]} (${s.kind_a})` : "—"}
                    </td>
                    <td data-label="B:" className="block text-slate-700 md:table-cell md:py-2 md:pr-4 before:mr-1 before:text-xs before:font-medium before:text-slate-500 before:content-[attr(data-label)] md:before:content-none">
                      {s.status_b ? `${STATUS_LABELS[s.status_b]} (${s.kind_b})` : "—"}
                    </td>
                    <td className="absolute right-0 top-3 md:static md:table-cell md:py-2">
                      <Badge tone={change.tone}>{change.label}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
