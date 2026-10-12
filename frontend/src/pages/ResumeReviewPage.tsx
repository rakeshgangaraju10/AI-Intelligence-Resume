import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { Button, LinkButton } from "../components/ui/Button";
import { Alert, Card, PageHeader } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { PageSpinner } from "../components/ui/Spinner";
import { EntrySectionEditor } from "../features/resumes/EntrySectionEditor";
import { ProfileEditor } from "../features/resumes/ProfileEditor";
import {
  CERTIFICATIONS_CONFIG,
  EDUCATION_CONFIG,
  EXPERIENCE_CONFIG,
  PROJECTS_CONFIG,
} from "../features/resumes/sectionConfigs";
import { SkillsEditor } from "../features/resumes/SkillsEditor";
import { useApiData } from "../hooks/useApiData";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatBytes, formatDateTime } from "../lib/format";
import { parseWarningMessage } from "../lib/messages";
import { toApiError } from "../services/api";
import { deleteResume, getExtraction, getResume, renameResume, reparseResume } from "../services/resumes";
import type { ResumeDetail, ResumeExtraction } from "../types/api";

export function ResumeReviewPage() {
  const { resumeId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const justUploaded = Boolean((location.state as { justUploaded?: boolean } | null)?.justUploaded);

  const { data, error, loading, setData } = useApiData(
    () => Promise.all([getResume(resumeId), getExtraction(resumeId)]),
    [resumeId],
  );
  useDocumentTitle(data ? `Review: ${data[0].title}` : "Review resume");

  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(justUploaded ? "Resume uploaded. Review what was extracted and correct anything that's wrong." : null);
  const [busy, setBusy] = useState<"rename" | "reparse" | "delete" | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [showText, setShowText] = useState(false);

  if (loading && !data) return <PageSpinner label="Loading resume" />;
  if (error?.status === 404) {
    return (
      <Alert tone="error" title="Resume not found">
        It may have been deleted. <Link to="/resumes" className="underline">Back to resumes</Link>
      </Alert>
    );
  }
  if (error || !data) return <Alert tone="error">{error?.message ?? "Couldn't load this resume."}</Alert>;

  const [resume, extraction] = data;

  function update(next: Partial<ResumeExtraction>, nextResume?: ResumeDetail) {
    setData((current) => (current ? [nextResume ?? current[0], { ...current[1], ...next }] : current));
  }

  async function handleRename(event: FormEvent) {
    event.preventDefault();
    setActionError(null);
    setBusy("rename");
    try {
      const updated = await renameResume(resumeId, titleDraft.trim());
      update({ title: updated.title }, updated);
      setEditingTitle(false);
    } catch (err) {
      const apiError = toApiError(err);
      setActionError(apiError.fieldMessage("title") ?? apiError.message);
    } finally {
      setBusy(null);
    }
  }

  async function handleReparse() {
    if (!window.confirm("Run the parser again? Entries you added, edited or confirmed are kept; unconfirmed detected entries are replaced.")) return;
    setActionError(null);
    setBusy("reparse");
    try {
      const fresh = await reparseResume(resumeId);
      update(fresh);
      setNotice("Parsing finished. Your own edits were kept.");
    } catch (err) {
      setActionError(toApiError(err).message);
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${resume.title}"? The PDF, all extracted data and its analyses will be permanently removed.`)) return;
    setBusy("delete");
    try {
      await deleteResume(resumeId);
      navigate("/resumes", { replace: true });
    } catch (err) {
      setActionError(toApiError(err).message);
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={resume.title}
        description={`${resume.original_filename} · ${formatBytes(resume.file_size)} · ${resume.page_count} page${resume.page_count === 1 ? "" : "s"} · uploaded ${formatDateTime(resume.created_at)}`}
        actions={
          <>
            <LinkButton to={`/jobs?resume=${resume.id}`}>Compare with a job</LinkButton>
            <Button variant="secondary" onClick={() => { setTitleDraft(resume.title); setEditingTitle(true); }}>
              Rename
            </Button>
            <Button variant="secondary" onClick={handleReparse} loading={busy === "reparse"}>
              Re-run parser
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={busy === "delete"}>
              Delete
            </Button>
          </>
        }
      />

      {notice && <Alert tone="success">{notice}</Alert>}
      {actionError && <Alert tone="error">{actionError}</Alert>}

      {editingTitle && (
        <form onSubmit={handleRename} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4">
          <div className="min-w-[14rem] flex-1">
            <TextField label="Resume title" value={titleDraft} maxLength={150} required onChange={(e) => setTitleDraft(e.target.value)} />
          </div>
          <Button type="submit" loading={busy === "rename"} disabled={!titleDraft.trim()}>
            Save title
          </Button>
          <Button variant="secondary" onClick={() => setEditingTitle(false)}>
            Cancel
          </Button>
        </form>
      )}

      {extraction.error_code === "parse_failed" && (
        <Alert tone="warning" title="Automatic extraction failed">
          Your PDF was saved and its text was read, but structured parsing failed. Try "Re-run parser", or add your details
          manually below.
        </Alert>
      )}

      {extraction.parse_warnings.length > 0 && (
        <Alert tone="warning" title="Some information couldn't be extracted automatically">
          <ul className="list-disc space-y-1 pl-5">
            {extraction.parse_warnings.map((code) => (
              <li key={code}>{parseWarningMessage(code)}</li>
            ))}
          </ul>
        </Alert>
      )}

      <p className="text-sm text-slate-600">
        Items marked <strong>“Detected · please review”</strong> were found automatically. Confirm what's correct, edit or
        delete what isn't, and add anything missing. Nothing is invented: empty fields mean the information wasn't found.
      </p>

      <ProfileEditor resumeId={resumeId} profile={extraction.profile} onSaved={(profile) => update({ profile })} />
      <SkillsEditor resumeId={resumeId} skills={extraction.skills} onChange={(skills) => update({ skills })} />
      <EntrySectionEditor resumeId={resumeId} config={EXPERIENCE_CONFIG} entries={extraction.experience} onChange={(experience) => update({ experience })} />
      <EntrySectionEditor resumeId={resumeId} config={PROJECTS_CONFIG} entries={extraction.projects} onChange={(projects) => update({ projects })} />
      <EntrySectionEditor resumeId={resumeId} config={EDUCATION_CONFIG} entries={extraction.education} onChange={(education) => update({ education })} />
      <EntrySectionEditor resumeId={resumeId} config={CERTIFICATIONS_CONFIG} entries={extraction.certifications} onChange={(certifications) => update({ certifications })} />

      <Card
        title="Extracted text"
        actions={
          <Button size="sm" variant="secondary" onClick={() => setShowText((v) => !v)} aria-expanded={showText}>
            {showText ? "Hide" : "Show"} text ({resume.char_count.toLocaleString()} characters)
          </Button>
        }
      >
        {showText ? (
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-xs text-slate-800">{resume.extracted_text}</pre>
        ) : (
          <p className="text-sm text-slate-600">The raw text read from your PDF, useful for checking what the parser saw.</p>
        )}
      </Card>
    </div>
  );
}
