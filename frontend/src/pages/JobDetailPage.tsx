import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert, Badge, Card, PageHeader } from "../components/ui/Feedback";
import { SelectField, TextArea, TextField } from "../components/ui/Field";
import { PageSpinner } from "../components/ui/Spinner";
import { ScoreBadge } from "../features/analyses/ScoreBadge";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { EXPERIENCE_LEVEL_LABELS, formatDate } from "../lib/format";
import { runAnalysis, listAnalyses } from "../services/analyses";
import { toApiError } from "../services/api";
import { addRequirement, deleteJob, deleteRequirement, getJob, suggestRequirements, updateJob, updateRequirement } from "../services/jobs";
import { listResumes } from "../services/resumes";
import type { ExperienceLevel, JobDetail, JobRequirement, RequirementKind } from "../types/api";

const KIND_OPTIONS = [
  { value: "required", label: "Required" },
  { value: "preferred", label: "Preferred" },
];
const WEIGHT_OPTIONS = [1, 2, 3, 4, 5].map((w) => ({ value: String(w), label: w === 1 ? "1 (normal)" : w === 5 ? "5 (critical)" : String(w) }));
const LEVEL_OPTIONS = Object.entries(EXPERIENCE_LEVEL_LABELS).map(([value, label]) => ({ value, label }));

function RequirementRow({ jobId, req, onSaved, onDeleted }: { jobId: number; req: JobRequirement; onSaved: (r: JobRequirement) => void; onDeleted: (id: number) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function change(data: Partial<Pick<JobRequirement, "kind" | "weight">>) {
    setBusy(true);
    setError(null);
    try {
      onSaved(await updateRequirement(jobId, req.id, data));
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await deleteRequirement(jobId, req.id);
      onDeleted(req.id);
    } catch (err) {
      setError(toApiError(err).message);
      setBusy(false);
    }
  }

  return (
    <tr className="align-top">
      <td className="py-3 pr-3">
        <div className="font-medium text-slate-900">{req.name}</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {req.source === "extracted" ? <Badge tone="amber">Suggested</Badge> : <Badge tone="sky">Added by you</Badge>}
          {!req.canonical && <Badge>custom</Badge>}
        </div>
        {req.evidence && (
          <p className="mt-1 max-w-md text-xs text-slate-500">
            From: <q>{req.evidence}</q>
          </p>
        )}
        {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
      </td>
      <td className="py-3 pr-3">
        <label className="sr-only" htmlFor={`kind-${req.id}`}>
          Importance of {req.name}
        </label>
        <select
          id={`kind-${req.id}`}
          value={req.kind}
          disabled={busy}
          onChange={(e) => change({ kind: e.target.value as RequirementKind })}
          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
        >
          {KIND_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </td>
      <td className="py-3 pr-3">
        <label className="sr-only" htmlFor={`weight-${req.id}`}>
          Weight of {req.name}
        </label>
        <select
          id={`weight-${req.id}`}
          value={String(req.weight)}
          disabled={busy}
          onChange={(e) => change({ weight: Number(e.target.value) })}
          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
        >
          {WEIGHT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </td>
      <td className="py-3 text-right">
        <Button size="sm" variant="ghost" onClick={remove} disabled={busy} aria-label={`Remove ${req.name}`}>
          Remove
        </Button>
      </td>
    </tr>
  );
}

function RunAnalysisPanel({ job, initialResumeId }: { job: JobDetail; initialResumeId: string | null }) {
  const navigate = useNavigate();
  const resumes = useApiData(() => listResumes(1, 100), []);
  const history = useApiData(() => listAnalyses({ job: job.id, pageSize: 5 }), [job.id]);
  const [resumeId, setResumeId] = useState(initialResumeId ?? "");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!resumeId && resumes.data?.results.length) setResumeId(resumes.data.results[0].id);
  }, [resumes.data, resumeId]);

  async function handleRun(event: FormEvent) {
    event.preventDefault();
    if (!resumeId) return;
    setRunning(true);
    setError(null);
    try {
      const analysis = await runAnalysis(resumeId, job.id);
      navigate(`/analyses/${analysis.id}`);
    } catch (err) {
      const apiError = toApiError(err);
      setError(apiError.fieldMessage("job") ?? apiError.fieldMessage("resume") ?? apiError.message);
      setRunning(false);
    }
  }

  const noRequirements = job.requirements.length === 0;

  return (
    <Card title="Compare a resume with this job">
      {resumes.loading ? (
        <PageSpinner label="Loading resumes" />
      ) : !resumes.data?.results.length ? (
        <p className="text-sm text-slate-600">
          You haven't uploaded a resume yet.{" "}
          <Link to="/resumes/upload" className="font-medium text-indigo-700 underline">
            Upload one
          </Link>{" "}
          to run an analysis.
        </p>
      ) : (
        <form onSubmit={handleRun} className="space-y-3">
          {error && <Alert tone="error">{error}</Alert>}
          {noRequirements && <Alert tone="warning">Add at least one required or preferred skill before running an analysis.</Alert>}
          <SelectField
            label="Resume"
            value={resumeId}
            onChange={(e) => setResumeId(e.target.value)}
            options={resumes.data.results.map((r) => ({ value: r.id, label: `${r.title} (${formatDate(r.created_at)})` }))}
          />
          <Button type="submit" loading={running} disabled={noRequirements || !resumeId}>
            Run analysis
          </Button>
        </form>
      )}
      {history.data && history.data.results.length > 0 && (
        <div className="mt-6 border-t border-slate-100 pt-4">
          <h3 className="text-sm font-semibold text-slate-800">Previous analyses for this job</h3>
          <ul className="mt-2 divide-y divide-slate-100">
            {history.data.results.map((a) => (
              <li key={a.id}>
                <Link to={`/analyses/${a.id}`} className="flex items-center justify-between gap-3 py-2 text-sm hover:bg-slate-50">
                  <span className="truncate">
                    {a.resume_title} · {formatDate(a.created_at)}
                  </span>
                  <ScoreBadge score={a.score} />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export function JobDetailPage() {
  const params = useParams();
  const jobId = Number(params.jobId);
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: job, error, loading, setData } = useApiData(() => getJob(jobId), [jobId]);
  useDocumentTitle(job ? job.title : "Job");

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ title: "", company: "", experience_level: "unspecified" as ExperienceLevel, description: "" });
  const [newReq, setNewReq] = useState({ name: "", kind: "required" as RequirementKind, weight: 1 });
  const [busy, setBusy] = useState<"save" | "suggest" | "add" | "delete" | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(
    (location.state as { created?: boolean } | null)?.created ? { tone: "success", text: "Job saved. Review the suggested skills and their importance below." } : null,
  );

  if (!Number.isInteger(jobId)) return <Alert tone="error">Invalid job link.</Alert>;
  if (loading && !job) return <PageSpinner label="Loading job" />;
  if (error?.status === 404) {
    return (
      <Alert tone="error" title="Job not found">
        <Link to="/jobs" className="underline">Back to jobs</Link>
      </Alert>
    );
  }
  if (error || !job) return <Alert tone="error">{error?.message ?? "Couldn't load this job."}</Alert>;

  const setRequirements = (requirements: JobRequirement[]) => setData((j) => (j ? { ...j, requirements } : j));

  async function wrap(kind: "save" | "suggest" | "add" | "delete", fn: () => Promise<void>) {
    setBusy(kind);
    setMessage(null);
    try {
      await fn();
    } catch (err) {
      const apiError = toApiError(err);
      const fieldMessages = Object.values(apiError.fields).flat().map((f) => f.message);
      setMessage({ tone: "error", text: fieldMessages[0] ?? apiError.message });
    } finally {
      setBusy(null);
    }
  }

  const required = job.requirements.filter((r) => r.kind === "required");
  const preferred = job.requirements.filter((r) => r.kind === "preferred");

  return (
    <div className="space-y-6">
      <PageHeader
        title={job.title}
        description={[job.company, EXPERIENCE_LEVEL_LABELS[job.experience_level], `added ${formatDate(job.created_at)}`].filter(Boolean).join(" · ")}
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setDraft({ title: job.title, company: job.company, experience_level: job.experience_level, description: job.description });
                setEditing(true);
              }}
            >
              Edit details
            </Button>
            <Button
              variant="danger"
              loading={busy === "delete"}
              onClick={() => {
                if (!window.confirm(`Delete "${job.title}" and all analyses that used it?`)) return;
                void wrap("delete", async () => {
                  await deleteJob(job.id);
                  navigate("/jobs", { replace: true });
                });
              }}
            >
              Delete
            </Button>
          </>
        }
      />

      {message && <Alert tone={message.tone}>{message.text}</Alert>}

      {editing && (
        <Card title="Edit job details">
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void wrap("save", async () => {
                const updated = await updateJob(job.id, { ...draft, title: draft.title.trim(), company: draft.company.trim() });
                setData(updated);
                setEditing(false);
              });
            }}
          >
            <TextField label="Job title" required value={draft.title} maxLength={200} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField label="Company" value={draft.company} maxLength={200} onChange={(e) => setDraft({ ...draft, company: e.target.value })} />
              <SelectField
                label="Experience level"
                options={LEVEL_OPTIONS}
                value={draft.experience_level}
                onChange={(e) => setDraft({ ...draft, experience_level: e.target.value as ExperienceLevel })}
              />
            </div>
            <TextArea label="Job description" rows={8} maxLength={20000} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditing(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={busy === "save"} disabled={!draft.title.trim()}>
                Save changes
              </Button>
            </div>
          </form>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card
            title={`Skills (${required.length} required, ${preferred.length} preferred)`}
            actions={
              job.description ? (
                <Button
                  size="sm"
                  variant="secondary"
                  loading={busy === "suggest"}
                  onClick={() =>
                    void wrap("suggest", async () => {
                      const result = await suggestRequirements(job.id);
                      setData(result.job);
                      setMessage({
                        tone: "success",
                        text: result.added ? `Added ${result.added} skill${result.added === 1 ? "" : "s"} found in the description.` : "No new skills were found in the description.",
                      });
                    })
                  }
                >
                  Suggest from description
                </Button>
              ) : undefined
            }
          >
            <p className="mb-3 text-sm text-slate-600">
              The score is weighted: required skills count for most of it, and a higher weight makes a skill count more. Review
              suggested skills before running an analysis.
            </p>
            {job.requirements.length === 0 ? (
              <p className="text-sm text-slate-600">No skills yet. Add the skills this job asks for.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th scope="col" className="pb-2 pr-3 font-medium">Skill</th>
                      <th scope="col" className="pb-2 pr-3 font-medium">Importance</th>
                      <th scope="col" className="pb-2 pr-3 font-medium">Weight</th>
                      <th scope="col" className="pb-2 font-medium"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {job.requirements.map((req) => (
                      <RequirementRow
                        key={req.id}
                        jobId={job.id}
                        req={req}
                        onSaved={(saved) => setRequirements(job.requirements.map((r) => (r.id === saved.id ? saved : r)))}
                        onDeleted={(id) => setRequirements(job.requirements.filter((r) => r.id !== id))}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <form
              className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-4"
              onSubmit={(e) => {
                e.preventDefault();
                if (!newReq.name.trim()) return;
                void wrap("add", async () => {
                  const created = await addRequirement(job.id, { ...newReq, name: newReq.name.trim() });
                  setRequirements([...job.requirements, created]);
                  setNewReq({ name: "", kind: newReq.kind, weight: 1 });
                });
              }}
            >
              <div className="min-w-[10rem] flex-1">
                <TextField label="Add a skill" value={newReq.name} maxLength={100} onChange={(e) => setNewReq({ ...newReq, name: e.target.value })} />
              </div>
              <SelectField label="Importance" options={KIND_OPTIONS} value={newReq.kind} onChange={(e) => setNewReq({ ...newReq, kind: e.target.value as RequirementKind })} />
              <SelectField label="Weight" options={WEIGHT_OPTIONS} value={String(newReq.weight)} onChange={(e) => setNewReq({ ...newReq, weight: Number(e.target.value) })} />
              <Button type="submit" loading={busy === "add"} disabled={!newReq.name.trim()}>
                Add
              </Button>
            </form>
          </Card>

          {job.description && (
            <Card title="Job description">
              <p className="whitespace-pre-line text-sm text-slate-700">{job.description}</p>
            </Card>
          )}
        </div>

        <div>
          <RunAnalysisPanel job={job} initialResumeId={searchParams.get("resume")} />
        </div>
      </div>
    </div>
  );
}
