import { type FormEvent, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Alert, Card } from "../../components/ui/Feedback";
import { TextField } from "../../components/ui/Field";
import { toApiError } from "../../services/api";
import { importJobFromUrl } from "../../services/jobs";
import type { ImportedJob } from "../../types/api";

/** "Paste a job link" box: reads the posting and hands it to the Add-job form. */
export function JobLinkImport({ onImported }: { onImported: (job: ImportedJob) => void }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imported, setImported] = useState<ImportedJob | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const link = url.trim();
    if (!/^https?:\/\/\S+$/i.test(link)) {
      setError("Paste the full link, starting with https://");
      return;
    }
    setLoading(true);
    setError(null);
    setImported(null);
    try {
      const job = await importJobFromUrl(link);
      setImported(job);
      onImported(job);
    } catch (err) {
      const apiError = toApiError(err);
      setError(apiError.fieldMessage("url") ?? apiError.message);
    } finally {
      setLoading(false);
    }
  }

  let host = "";
  try {
    host = imported ? new URL(imported.source_url).hostname : "";
  } catch {
    host = "";
  }

  return (
    <Card className="mb-4" title="Have a job link? Paste it here">
      <form onSubmit={handleSubmit} noValidate className="flex flex-wrap items-end gap-2">
        <div className="min-w-[16rem] flex-1">
          <TextField
            label="Job posting link"
            type="url"
            inputMode="url"
            placeholder="https://careers.company.com/jobs/123"
            hint="Company career pages, Greenhouse, Lever, Workday… LinkedIn and Indeed don't allow this: copy and paste their text instead."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        <Button type="submit" loading={loading} disabled={!url.trim()}>
          Import job
        </Button>
      </form>
      {error && (
        <div className="mt-3">
          <Alert tone="error">{error}</Alert>
        </div>
      )}
      {imported && (
        <div className="mt-3 space-y-2">
          <Alert tone="success">
            Imported “{imported.title}”{host ? ` from ${host}` : ""}. Review the details below, then click Save job.
          </Alert>
          {imported.warnings.map((w) => (
            <Alert key={w} tone="warning">
              {w}
            </Alert>
          ))}
        </div>
      )}
    </Card>
  );
}
