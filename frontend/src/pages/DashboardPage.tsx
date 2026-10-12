import { Link } from "react-router";

import { LinkButton } from "../components/ui/Button";
import { Alert, Card, EmptyState, PageHeader } from "../components/ui/Feedback";
import { PageSpinner } from "../components/ui/Spinner";
import { ScoreBadge } from "../features/analyses/ScoreBadge";
import { useAuth } from "../features/auth/AuthContext";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDate } from "../lib/format";
import { listAnalyses } from "../services/analyses";
import { listResumes } from "../services/resumes";

export function DashboardPage() {
  useDocumentTitle("Dashboard");
  const { user } = useAuth();
  // Counts come from the paginated list endpoints: real numbers, nothing invented.
  const { data, error, loading } = useApiData(
    () => Promise.all([listResumes(1, 5), listAnalyses({ pageSize: 5 })]),
    [],
  );

  if (loading) return <PageSpinner />;
  if (error || !data) return <Alert tone="error">{error?.message ?? "Couldn't load your dashboard."}</Alert>;

  const [resumes, analyses] = data;
  const isNewUser = resumes.count === 0;

  return (
    <div>
      <PageHeader
        title={`Welcome${user ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Upload a resume, add a job description and see how they match."
        actions={
          <>
            <LinkButton to="/resumes/upload">Upload resume</LinkButton>
            <LinkButton to="/jobs/new" variant="secondary">
              Analyze against a job
            </LinkButton>
          </>
        }
      />

      {isNewUser ? (
        <EmptyState
          title="Start by uploading your resume"
          action={<LinkButton to="/resumes/upload">Upload a PDF resume</LinkButton>}
        >
          CareerForge reads your PDF, extracts your skills and experience, and lets you correct anything before comparing it
          with job descriptions.
        </EmptyState>
      ) : (
        <>
          <dl className="mb-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <dt className="text-sm text-slate-600">Resumes uploaded</dt>
              <dd className="mt-1 text-3xl font-bold text-slate-900">{resumes.count}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <dt className="text-sm text-slate-600">Analyses completed</dt>
              <dd className="mt-1 text-3xl font-bold text-slate-900">{analyses.count}</dd>
            </div>
          </dl>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Recent analyses" actions={<Link to="/analyses" className="text-sm font-medium text-indigo-700 underline">View all</Link>}>
              {analyses.results.length === 0 ? (
                <p className="text-sm text-slate-600">
                  No analyses yet.{" "}
                  <Link to="/jobs/new" className="font-medium text-indigo-700 underline">
                    Add a job description
                  </Link>{" "}
                  to run your first one.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {analyses.results.map((a) => (
                    <li key={a.id}>
                      <Link to={`/analyses/${a.id}`} className="flex items-center justify-between gap-3 py-3 hover:bg-slate-50">
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-slate-900">{a.job_title}</span>
                          <span className="block truncate text-xs text-slate-500">
                            {a.resume_title} · {formatDate(a.created_at)}
                          </span>
                        </span>
                        <ScoreBadge score={a.score} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card title="Recent resumes" actions={<Link to="/resumes" className="text-sm font-medium text-indigo-700 underline">View all</Link>}>
              <ul className="divide-y divide-slate-100">
                {resumes.results.map((r) => (
                  <li key={r.id}>
                    <Link to={`/resumes/${r.id}`} className="flex items-center justify-between gap-3 py-3 hover:bg-slate-50">
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-slate-900">{r.title}</span>
                        <span className="block truncate text-xs text-slate-500">
                          {r.original_filename} · {formatDate(r.created_at)}
                        </span>
                      </span>
                      <span className="text-xs text-slate-500">{r.page_count} page{r.page_count === 1 ? "" : "s"}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
