import type { SectionEntry } from "../../services/resumes";
import type { ResumeCertification, ResumeEducation, ResumeExperience, ResumeProject } from "../../types/api";
import type { SectionConfig } from "./EntrySectionEditor";

const join = (...parts: (string | undefined)[]) => parts.filter(Boolean).join(" · ");
const range = (start: string, end: string, current = false) => {
  const to = current ? "Present" : end;
  if (start && to) return `${start} – ${to}`;
  return start || to || "";
};

export const EDUCATION_CONFIG: SectionConfig = {
  section: "education",
  title: "Education",
  addLabel: "Add education",
  emptyText: "No education entries. Add your degrees or school qualifications.",
  fields: [
    { name: "degree", label: "Degree / qualification", maxLength: 200 },
    { name: "field_of_study", label: "Field of study", maxLength: 200 },
    { name: "institution", label: "Institution", maxLength: 200, wide: true },
    { name: "start_date", label: "Start", maxLength: 30, hint: "As written, e.g. 2021 or Aug 2021" },
    { name: "end_date", label: "End", maxLength: 30 },
    { name: "grade", label: "Grade / CGPA", maxLength: 50 },
    { name: "description", label: "Details", type: "textarea" },
  ],
  heading: (e: SectionEntry) => {
    const edu = e as ResumeEducation;
    return join(edu.degree, edu.field_of_study) || edu.institution;
  },
  subheading: (e: SectionEntry) => {
    const edu = e as ResumeEducation;
    return join(edu.degree || edu.field_of_study ? edu.institution : "", range(edu.start_date, edu.end_date), edu.grade);
  },
  validate: (v) => (!v.institution && !v.degree ? "Provide at least an institution or a degree." : null),
};

export const EXPERIENCE_CONFIG: SectionConfig = {
  section: "experience",
  title: "Work experience",
  addLabel: "Add experience",
  emptyText: "No experience entries. Internships, part-time and freelance work count.",
  fields: [
    { name: "title", label: "Job title", maxLength: 200 },
    { name: "company", label: "Company", maxLength: 200 },
    { name: "location", label: "Location", maxLength: 120 },
    { name: "start_date", label: "Start", maxLength: 30, hint: "As written, e.g. Jun 2024" },
    { name: "end_date", label: "End", maxLength: 30, hint: "Leave empty if this is your current role" },
    { name: "is_current", label: "I currently work here", type: "checkbox" },
    { name: "description", label: "What you did", type: "textarea", hint: "One achievement per line works well." },
  ],
  heading: (e: SectionEntry) => {
    const exp = e as ResumeExperience;
    return [exp.title, exp.company].filter(Boolean).join(" at ");
  },
  subheading: (e: SectionEntry) => {
    const exp = e as ResumeExperience;
    return join(exp.location, range(exp.start_date, exp.end_date, exp.is_current));
  },
  validate: (v) => {
    if (!v.title && !v.company) return "Provide at least a job title or a company.";
    if (v.is_current && v.end_date) return "Leave the end date empty for a current position.";
    return null;
  },
};

export const PROJECTS_CONFIG: SectionConfig = {
  section: "projects",
  title: "Projects",
  addLabel: "Add project",
  emptyText: "No projects. Projects are often the best evidence of your skills.",
  fields: [
    { name: "name", label: "Project name", maxLength: 200 },
    { name: "url", label: "Link", maxLength: 300, hint: "Repository or demo URL (optional)" },
    { name: "technologies", label: "Technologies", type: "list", wide: true, hint: "Comma-separated, e.g. Django, PostgreSQL, React" },
    { name: "description", label: "Description", type: "textarea" },
  ],
  heading: (e: SectionEntry) => (e as ResumeProject).name,
  subheading: (e: SectionEntry) => {
    const p = e as ResumeProject;
    return join(p.technologies.join(", "), p.url);
  },
  validate: (v) => (!v.name ? "Give the project a name." : null),
};

export const CERTIFICATIONS_CONFIG: SectionConfig = {
  section: "certifications",
  title: "Certifications",
  addLabel: "Add certification",
  emptyText: "No certifications. Add only certifications you have actually earned.",
  fields: [
    { name: "name", label: "Certification", maxLength: 200, wide: true },
    { name: "issuer", label: "Issuer", maxLength: 200 },
    { name: "issue_date", label: "Date", maxLength: 30 },
    { name: "credential_url", label: "Credential link", maxLength: 300, wide: true },
  ],
  heading: (e: SectionEntry) => (e as ResumeCertification).name,
  subheading: (e: SectionEntry) => {
    const c = e as ResumeCertification;
    return join(c.issuer, c.issue_date);
  },
  validate: (v) => (!v.name ? "Enter the certification name." : null),
};
