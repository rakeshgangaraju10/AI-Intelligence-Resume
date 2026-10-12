import { useState } from "react";
import { useNavigate } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert, Card, PageHeader, ProgressBar } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { ResumeDropzone } from "../features/resumes/ResumeDropzone";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatBytes } from "../lib/format";
import { UPLOAD_ERROR_MESSAGES } from "../lib/messages";
import { maxUploadBytes, validatePdfFile } from "../lib/uploadValidation";
import { toApiError } from "../services/api";
import { uploadResume } from "../services/resumes";

type Phase = "idle" | "uploading" | "processing";

export function ResumeUploadPage() {
  useDocumentTitle("Upload resume");
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const maxBytes = maxUploadBytes();

  function selectFile(selected: File) {
    const problem = validatePdfFile(selected, maxBytes);
    setError(problem);
    setFile(problem ? null : selected);
    if (!problem && !title) setTitle(selected.name.replace(/\.pdf$/i, "").slice(0, 150));
  }

  async function handleUpload() {
    if (!file) return;
    setError(null);
    setPhase("uploading");
    setProgress(0);
    try {
      const resume = await uploadResume(file, title.trim() || undefined, (percent) => {
        setProgress(percent);
        if (percent >= 100) setPhase("processing");
      });
      navigate(`/resumes/${resume.id}`, { state: { justUploaded: true } });
    } catch (err) {
      const apiError = toApiError(err);
      const code = apiError.fieldCode("file") ?? apiError.code;
      setError(UPLOAD_ERROR_MESSAGES[code] ?? apiError.fieldMessage("file") ?? apiError.message);
      setPhase("idle");
    }
  }

  const busy = phase !== "idle";

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Upload resume" description="Your PDF is stored privately and only you can access it." />
      <Card>
        <div className="space-y-5">
          <ResumeDropzone onFile={selectFile} disabled={busy} maxLabel={formatBytes(maxBytes)} />

          {error && <Alert tone="error" title="This file can't be used">{error}</Alert>}

          {file && (
            <div className="rounded-md bg-slate-50 px-4 py-3 text-sm">
              <span className="font-medium text-slate-900">{file.name}</span>
              <span className="text-slate-500"> · {formatBytes(file.size)}</span>
            </div>
          )}

          {file && (
            <TextField
              label="Title (optional)"
              hint="A label to tell your resume versions apart, e.g. 'Backend roles v2'."
              value={title}
              maxLength={150}
              disabled={busy}
              onChange={(e) => setTitle(e.target.value)}
            />
          )}

          {busy && (
            <div className="space-y-2" aria-live="polite">
              <ProgressBar value={progress} label="Upload progress" />
              <p className="text-sm text-slate-600">
                {phase === "uploading" ? `Uploading… ${progress}%` : "Extracting text and detecting sections…"}
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button onClick={handleUpload} disabled={!file} loading={busy}>
              Upload and analyze
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
