import { useState } from "react";
import { Link } from "react-router";

import { Button, LinkButton } from "../components/ui/Button";
import { Alert, Badge, EmptyState, PageHeader } from "../components/ui/Feedback";
import { PageSpinner } from "../components/ui/Spinner";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatBytes, formatDate } from "../lib/format";
import { toApiError } from "../services/api";
import { deleteResume, listResumes } from "../services/resumes";

export function ResumesPage() {
  useDocumentTitle("Resumes");
  const [page, setPage] = useState(1);
  const { data, error, loading, reload } = useApiData(() => listResumes(page), [page]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string, title: string) {
    if (!window.confirm(`Delete "${title}"? This permanently removes the PDF, its extracted data and its analyses.`)) return;
    setActionError(null);
    setDeletingId(id);
    try {
      await deleteResume(id);
      await reload();
    } catch (err) {
      setActionError(toApiError(err).message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Resumes"
        description="Each upload is kept as its own version, so you can compare versions against the same job."
        actions={<LinkButton to="/resumes/upload">Upload resume</LinkButton>}
      />
      {actionError && <div className="mb-4"><Alert tone="error">{actionError}</Alert></div>}
      {loading && !data ? (
        <PageSpinner />
      ) : error ? (
        <Alert tone="error">{error.message}</Alert>
      ) : !data || data.count === 0 ? (
        <EmptyState title="No resumes yet" action={<LinkButton to="/resumes/upload">Upload your first resume</LinkButton>}>
          Upload a text-based PDF. You'll be able to review and correct everything that's extracted.
        </EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white shadow-sm">
            {data.results.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <Link to={`/resumes/${r.id}`} className="font-medium text-indigo-800 underline-offset-2 hover:underline">
                    {r.title}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {r.original_filename} · {formatBytes(r.file_size)} · {r.page_count} page{r.page_count === 1 ? "" : "s"} · uploaded{" "}
                    {formatDate(r.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {r.status === "parsed" ? <Badge tone="green">Parsed</Badge> : <Badge tone="amber">Needs review</Badge>}
                  <LinkButton to={`/resumes/${r.id}`} variant="secondary" size="sm">
                    Review
                  </LinkButton>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id, r.title)} loading={deletingId === r.id}>
                    Delete
                  </Button>
                </div>
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
