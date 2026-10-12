import type { AnalysisDetail, AnalysisListItem, Paginated } from "../types/api";
import { api, request } from "./api";

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
