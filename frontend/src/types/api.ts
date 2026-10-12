// Types mirroring the Django REST Framework serializers (see docs/api-documentation.md).

export interface User {
  id: number;
  email: string;
  full_name: string;
  date_joined: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- Resumes ---------------------------------------------------------------------

export type ResumeStatus = "text_extracted" | "parsed" | "failed";
export type EntrySource = "parser" | "user";

export interface ResumeListItem {
  id: string;
  title: string;
  original_filename: string;
  file_size: number;
  page_count: number;
  status: ResumeStatus;
  created_at: string;
  updated_at: string;
}

export interface ResumeDetail extends ResumeListItem {
  error_code: string;
  parse_warnings: string[];
  parsed_at: string | null;
  char_count: number;
  extracted_text: string;
}

export interface ResumeProfile {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  links: string[];
  summary: string;
  user_edited: boolean;
  updated_at: string;
}

interface EntryBase {
  id: number;
  source: EntrySource;
  is_verified: boolean;
  position: number;
  created_at: string;
  updated_at: string;
}

export interface ResumeSkill extends EntryBase {
  name: string;
  canonical: boolean;
  section: string;
  evidence: string;
}

export interface ResumeEducation extends EntryBase {
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  grade: string;
  description: string;
}

export interface ResumeExperience extends EntryBase {
  title: string;
  company: string;
  location: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
}

export interface ResumeProject extends EntryBase {
  name: string;
  description: string;
  technologies: string[];
  url: string;
}

export interface ResumeCertification extends EntryBase {
  name: string;
  issuer: string;
  issue_date: string;
  credential_url: string;
}

export interface ResumeExtraction {
  id: string;
  title: string;
  status: ResumeStatus;
  error_code: string;
  parse_warnings: string[];
  parsed_at: string | null;
  profile: ResumeProfile | null;
  skills: ResumeSkill[];
  education: ResumeEducation[];
  experience: ResumeExperience[];
  projects: ResumeProject[];
  certifications: ResumeCertification[];
}

export type ResumeSection = "education" | "experience" | "projects" | "certifications";

// --- Jobs ---------------------------------------------------------------------------

export type ExperienceLevel = "unspecified" | "internship" | "entry" | "mid" | "senior";
export type RequirementKind = "required" | "preferred";

export interface JobRequirement {
  id: number;
  name: string;
  kind: RequirementKind;
  weight: number;
  canonical: boolean;
  source: "extracted" | "user";
  evidence: string;
  created_at: string;
}

export interface JobListItem {
  id: number;
  title: string;
  company: string;
  experience_level: ExperienceLevel;
  required_count: number;
  preferred_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobDetail {
  id: number;
  title: string;
  company: string;
  experience_level: ExperienceLevel;
  description: string;
  requirements: JobRequirement[];
  created_at: string;
  updated_at: string;
}

export interface SkillInput {
  name: string;
  weight?: number;
}

export interface JobCreatePayload {
  title: string;
  company?: string;
  experience_level?: ExperienceLevel;
  description?: string;
  required_skills?: (string | SkillInput)[];
  preferred_skills?: (string | SkillInput)[];
  auto_extract?: boolean;
}

// --- Analyses ------------------------------------------------------------------------

export type SkillResultStatus = "matched" | "missing" | "related";

export interface Evidence {
  location: string;
  text: string;
}

export interface SkillResult {
  skill_name: string;
  kind: RequirementKind;
  weight: number;
  status: SkillResultStatus;
  evidence: Evidence[];
  related_to: string[];
  related_reason: string;
  explanation: string;
}

export interface CoverageBreakdown {
  matched_weight: number;
  total_weight: number;
  coverage: number | null;
}

export interface AnalysisBreakdown {
  formula: string;
  required: CoverageBreakdown;
  preferred: CoverageBreakdown;
  required_share: number;
  related_skills_count_toward_score: boolean;
}

export interface AnalysisListItem {
  id: number;
  resume: string;
  job: number;
  resume_title: string;
  job_title: string;
  score: number;
  required_coverage: number | null;
  preferred_coverage: number | null;
  matched_count: number;
  missing_count: number;
  algorithm_version: string;
  created_at: string;
}

export interface AnalysisDetail {
  id: number;
  resume: string;
  job: number;
  resume_title: string;
  job_title: string;
  score: number;
  score_label: string;
  required_coverage: number | null;
  preferred_coverage: number | null;
  required_share: number;
  algorithm_version: string;
  breakdown: AnalysisBreakdown;
  strengths: string[];
  improvements: string[];
  suggestions: string[];
  skill_results: SkillResult[];
  created_at: string;
}

// --- Errors ------------------------------------------------------------------------------

export interface FieldError {
  code: string;
  message: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    fields?: Record<string, FieldError[]>;
  };
}
