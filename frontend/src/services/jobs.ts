import type { JobCreatePayload, JobDetail, JobListItem, JobRequirement, Paginated, RequirementKind } from "../types/api";
import { api, request } from "./api";

export function listJobs(search = "", page = 1): Promise<Paginated<JobListItem>> {
  return request(() =>
    api.get<Paginated<JobListItem>>("/jobs/", { params: { page, ...(search ? { search } : {}) } }),
  );
}

export function getJob(id: number): Promise<JobDetail> {
  return request(() => api.get<JobDetail>(`/jobs/${id}/`));
}

export function createJob(payload: JobCreatePayload): Promise<JobDetail> {
  return request(() => api.post<JobDetail>("/jobs/", payload));
}

export function updateJob(
  id: number,
  data: Partial<Pick<JobDetail, "title" | "company" | "experience_level" | "description">>,
): Promise<JobDetail> {
  return request(() => api.patch<JobDetail>(`/jobs/${id}/`, data));
}

export function deleteJob(id: number): Promise<void> {
  return request(() => api.delete(`/jobs/${id}/`)).then(() => undefined);
}

export function suggestRequirements(id: number): Promise<{ added: number; job: JobDetail }> {
  return request(() => api.post<{ added: number; job: JobDetail }>(`/jobs/${id}/suggest-requirements/`));
}

export function addRequirement(
  jobId: number,
  data: { name: string; kind: RequirementKind; weight: number },
): Promise<JobRequirement> {
  return request(() => api.post<JobRequirement>(`/jobs/${jobId}/requirements/`, data));
}

export function updateRequirement(
  jobId: number,
  reqId: number,
  data: Partial<Pick<JobRequirement, "name" | "kind" | "weight">>,
): Promise<JobRequirement> {
  return request(() => api.patch<JobRequirement>(`/jobs/${jobId}/requirements/${reqId}/`, data));
}

export function deleteRequirement(jobId: number, reqId: number): Promise<void> {
  return request(() => api.delete(`/jobs/${jobId}/requirements/${reqId}/`)).then(() => undefined);
}
