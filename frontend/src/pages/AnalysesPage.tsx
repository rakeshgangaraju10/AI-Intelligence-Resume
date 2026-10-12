import { useState } from "react";
import { Link } from "react-router";

import { Button, LinkButton } from "../components/ui/Button";
import { Alert, EmptyState, PageHeader } from "../components/ui/Feedback";
import { SelectField } from "../components/ui/Field";
import { PageSpinner } from "../components/ui/Spinner";
import { ScoreBadge } from "../features/analyses/ScoreBadge";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDateTime, formatPercent } from "../lib/format";
import { deleteAnalysis, listAnalyses } from "../services/analyses";
import { toApiError } from "../services/api";
import { listResumes } from "../services/resumes";

export function AnalysesPage() {
  useDocumentTitle("Analyses");
  const [resumeFilter, setResumeFilter] = useState("");
  const [page, setPage] = useState(1);
  const resumes = useApiData(() => listResumes(1, 100), []);
  const { data, error, loading, reload } = useApiData(
    () => listAnalyses({ resume: resumeFilter || undefined, page }),
    [resumeFilter, page],
  );
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this analysis from your history?")) return;
    setActionError(null);
    try {
      await deleteAnalysis(id);
      await reload();
    } catch (err) {
      setActionError(toApiError(err).message);
    }
  }

  const resumeOptions = [
    { value: "", label: "All resumes" },
    ...(resumes.data?.results ?? []).map((r) => ({ value: r.id, label: r.title })),
  ];

  return (
    <div>
      <PageHeader
        title="Analysis history"
        description="Every analysis is saved as it was run, so you can track how resume edits change the match."
        actions={<LinkButton to="/jobs">Run a new analysis</LinkButton>}
      />
      <div className="mb-4 max-w-xs">
        <SelectField
          label="Filter by resume"
          options={resumeOptions}
          value={resumeFilter}
          onChange={(e) => {
            setPage(1);
            setResumeFilter(e.target.value);
          }}
        />
      </div>
      {actionError && (
        <div className="mb-4">
          <Alert tone="error">{actionError}</Alert>
        </div>
      )}
      {loading && !data ? (
        <PageSpinner />
      ) : error ? (
        <Alert tone="error">{error.message}</Alert>
      ) : !data || data.count === 0 ? (
        <EmptyState title="No analyses yet" action={<LinkButton to="/jobs">Choose a job to compare with</LinkButton>}>
          Open a saved job description, pick a resume and run an analysis.
        </EmptyState>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">Job</th>
                  <th scope="col" className="px-4 py-3 font-medium">Resume</th>
                  <th scope="col" className="px-4 py-3 font-medium">Score</th>
                  <th scope="col" className="px-4 py-3 font-medium">Required coverage</th>
                  <th scope="col" className="px-4 py-3 font-medium">Matched / not matched</th>
                  <th scope="col" className="px-4 py-3 font-medium">Date</th>
                  <th scope="col" className="px-4 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.results.map((a) => (
                  <tr key={a.id}>
                    <td className="px-4 py-3">
                      <Link to={`/analyses/${a.id}`} className="font-medium text-indigo-800 underline-offset-2 hover:underline">
                        {a.job_title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{a.resume_title}</td>
                    <td className="px-4 py-3">
                      <ScoreBadge score={a.score} />
                    </td>
                    <td className="px-4 py-3 text-slate-700">{formatPercent(a.required_coverage)}</td>
                    <td className="px-4 py-3 text-slate-700">
                      {a.matched_count} / {a.missing_count}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(a.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(a.id)} aria-label={`Delete analysis for ${a.job_title}`}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(data.previous || data.next) && (
            <nav aria-label="Pagination" className="mt-4 flex justify-between">
              <Button variant="secondary" size="sm" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button variant="secondary" size="sm" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
