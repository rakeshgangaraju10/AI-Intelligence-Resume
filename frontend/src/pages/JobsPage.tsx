import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";

import { Button, LinkButton } from "../components/ui/Button";
import { Alert, EmptyState, PageHeader } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { PageSpinner } from "../components/ui/Spinner";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { EXPERIENCE_LEVEL_LABELS, formatDate } from "../lib/format";
import { listJobs } from "../services/jobs";

export function JobsPage() {
  useDocumentTitle("Jobs");
  const [params] = useSearchParams();
  const resumeParam = params.get("resume");
  const suffix = resumeParam ? `?resume=${encodeURIComponent(resumeParam)}` : "";
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const { data, error, loading } = useApiData(() => listJobs(query, page), [query, page]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setQuery(search.trim());
  }

  return (
    <div>
      <PageHeader
        title="Job descriptions"
        description={resumeParam ? "Pick a job to compare your resume with, or add a new one." : "Saved job descriptions you can compare your resumes against."}
        actions={<LinkButton to={`/jobs/new${suffix}`}>Add job description</LinkButton>}
      />
      <form onSubmit={submitSearch} className="mb-4 flex flex-wrap items-end gap-2" role="search">
        <div className="min-w-[14rem] flex-1">
          <TextField label="Search by title or company" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {loading && !data ? (
        <PageSpinner />
      ) : error ? (
        <Alert tone="error">{error.message}</Alert>
      ) : !data || data.count === 0 ? (
        query ? (
          <EmptyState title="No matching jobs">Try a different search term.</EmptyState>
        ) : (
          <EmptyState
            title="No job descriptions yet"
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <LinkButton to={`/jobs/new${suffix}`}>Add your first job description</LinkButton>
                <LinkButton to={`/jobs/new?sample=python-developer${suffix ? "&" + suffix.slice(1) : ""}`} variant="secondary">
                  Try a sample job
                </LinkButton>
              </div>
            }
          >
            Paste a job posting from any job site, or start with one of our example jobs.
          </EmptyState>
        )
      ) : (
        <>
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white shadow-sm">
            {data.results.map((job) => (
              <li key={job.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <Link to={`/jobs/${job.id}${suffix}`} className="font-medium text-indigo-800 underline-offset-2 hover:underline">
                    {job.title}
                    {job.company && <span className="text-slate-600"> · {job.company}</span>}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {EXPERIENCE_LEVEL_LABELS[job.experience_level]} · {job.required_count} required · {job.preferred_count} preferred · added{" "}
                    {formatDate(job.created_at)}
                  </p>
                </div>
                <LinkButton to={`/jobs/${job.id}${suffix}`} variant="secondary" size="sm">
                  {resumeParam ? "Compare" : "Open"}
                </LinkButton>
              </li>
            ))}
          </ul>
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
