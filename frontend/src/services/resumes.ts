import type {
  Paginated,
  ResumeCertification,
  ResumeDetail,
  ResumeEducation,
  ResumeExperience,
  ResumeExtraction,
  ResumeListItem,
  ResumeProfile,
  ResumeProject,
  ResumeSection,
  ResumeSkill,
} from "../types/api";
import { api, ApiError, ensureCsrfCookie, request } from "./api";
import { markServerMaybeAsleep, wakeServer } from "./wake";

export function listResumes(page = 1, pageSize = 20): Promise<Paginated<ResumeListItem>> {
  return request(() => api.get<Paginated<ResumeListItem>>("/resumes/", { params: { page, page_size: pageSize } }));
}

export function getResume(id: string): Promise<ResumeDetail> {
  return request(() => api.get<ResumeDetail>(`/resumes/${id}/`));
}

export async function uploadResume(
  file: File,
  title: string | undefined,
  onProgress?: (percent: number) => void,
): Promise<ResumeDetail> {
  // On free hosting the server may be asleep: wake it before sending the file.
  await wakeServer();
  await ensureCsrfCookie();
  const send = () => {
    const form = new FormData();
    form.append("file", file);
    if (title) form.append("title", title);
    return request(() =>
      api.post<ResumeDetail>("/resumes/", form, {
        timeout: 120_000,
        onUploadProgress: (event) => {
          if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100));
        },
      }),
    );
  };
  try {
    return await send();
  } catch (err) {
    // No response at all (asleep/restarting server, dropped connection): wake it and retry once.
    if (err instanceof ApiError && err.status === 0) {
      markServerMaybeAsleep();
      if (await wakeServer({ force: true })) {
        onProgress?.(0);
        return send();
      }
    }
    throw err;
  }
}

export function renameResume(id: string, title: string): Promise<ResumeDetail> {
  return request(() => api.patch<ResumeDetail>(`/resumes/${id}/`, { title }));
}

export function deleteResume(id: string): Promise<void> {
  return request(() => api.delete(`/resumes/${id}/`)).then(() => undefined);
}

export function getExtraction(id: string): Promise<ResumeExtraction> {
  return request(() => api.get<ResumeExtraction>(`/resumes/${id}/extraction/`));
}

export function reparseResume(id: string): Promise<ResumeExtraction> {
  return request(() => api.post<ResumeExtraction>(`/resumes/${id}/reparse/`));
}

export function updateProfile(id: string, data: Partial<ResumeProfile>): Promise<ResumeProfile> {
  return request(() => api.patch<ResumeProfile>(`/resumes/${id}/profile/`, data));
}

// --- Skills ---

export function addSkill(resumeId: string, name: string): Promise<ResumeSkill> {
  return request(() => api.post<ResumeSkill>(`/resumes/${resumeId}/skills/`, { name }));
}

export function updateSkill(resumeId: string, skillId: number, data: Partial<Pick<ResumeSkill, "name" | "is_verified">>): Promise<ResumeSkill> {
  return request(() => api.patch<ResumeSkill>(`/resumes/${resumeId}/skills/${skillId}/`, data));
}

export function deleteSkill(resumeId: string, skillId: number): Promise<void> {
  return request(() => api.delete(`/resumes/${resumeId}/skills/${skillId}/`)).then(() => undefined);
}

// --- Generic list sections (education, experience, projects, certifications) ---

export type SectionEntry = ResumeEducation | ResumeExperience | ResumeProject | ResumeCertification;
export type EntryPayload = Record<string, string | boolean | string[]>;

export function addEntry<T extends SectionEntry>(resumeId: string, section: ResumeSection, data: EntryPayload): Promise<T> {
  return request(() => api.post<T>(`/resumes/${resumeId}/${section}/`, data));
}

export function updateEntry<T extends SectionEntry>(
  resumeId: string,
  section: ResumeSection,
  entryId: number,
  data: EntryPayload,
): Promise<T> {
  return request(() => api.patch<T>(`/resumes/${resumeId}/${section}/${entryId}/`, data));
}

export function deleteEntry(resumeId: string, section: ResumeSection, entryId: number): Promise<void> {
  return request(() => api.delete(`/resumes/${resumeId}/${section}/${entryId}/`)).then(() => undefined);
}
