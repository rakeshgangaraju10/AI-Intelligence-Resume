import { AxiosError } from "axios";

import type { AnalysisComparison, AnalysisDetail, AnalysisListItem, Paginated } from "../types/api";
import { api, request, toApiError } from "./api";

export interface AnalysisFilters {
  resume?: string;
  job?: number;
  page?: number;
  pageSize?: number;
}

export function listAnalyses(filters: AnalysisFilters = {}): Promise<Paginated<AnalysisListItem>> {
  const params: Record<string, string | number> = { page: filters.page ?? 1, page_size: filters.pageSize ?? 20 };
  if (filters.resume) params.resume = filters.resume;
  if (filters.job) params.job = filters.job;
  return request(() => api.get<Paginated<AnalysisListItem>>("/analyses/", { params }));
}

export function getAnalysis(id: number): Promise<AnalysisDetail> {
  return request(() => api.get<AnalysisDetail>(`/analyses/${id}/`));
}

export function runAnalysis(resumeId: string, jobId: number): Promise<AnalysisDetail> {
  return request(() => api.post<AnalysisDetail>("/analyses/", { resume: resumeId, job: jobId }));
}

export function deleteAnalysis(id: number): Promise<void> {
  return request(() => api.delete(`/analyses/${id}/`)).then(() => undefined);
}

export function compareAnalyses(a: number, b: number): Promise<AnalysisComparison> {
  return request(() => api.get<AnalysisComparison>("/analyses/compare/", { params: { a, b } }));
}

export interface ReportFile {
  blob: Blob;
  filename: string;
}

/** Pull the filename out of `Content-Disposition: attachment; filename="..."`. */
export function filenameFromDisposition(header: string | undefined, fallback: string): string {
  const match = header ? /filename="([^"]+)"/.exec(header) : null;
  return match?.[1] ?? fallback;
}

/**
 * Fetch the Markdown report as a Blob (cookies + CSRF stay with axios rather
 * than a bare link). Error bodies also arrive as Blobs, so parse them back into
 * the normal JSON error envelope before converting.
 */
export async function downloadReport(id: number): Promise<ReportFile> {
  try {
    const response = await api.get<Blob>(`/analyses/${id}/report/`, {
      responseType: "blob",
      headers: { Accept: "text/markdown, application/json" },
    });
    const header = response.headers["content-disposition"] as string | undefined;
    return { blob: response.data, filename: filenameFromDisposition(header, `careerforge-analysis-${id}.md`) };
  } catch (err) {
    if (err instanceof AxiosError && err.response?.data instanceof Blob) {
      try {
        err.response.data = JSON.parse(await err.response.data.text());
      } catch {
        // not JSON; toApiError falls back to a generic message
      }
    }
    throw toApiError(err);
  }
}

/** Hand a Blob to the browser as a file download. */
export function saveFile({ blob, filename }: ReportFile): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoke after the browser has started the download.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
