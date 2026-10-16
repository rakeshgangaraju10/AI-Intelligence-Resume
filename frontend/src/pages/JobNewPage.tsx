import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert, Card, PageHeader } from "../components/ui/Feedback";
import { SelectField, TextArea, TextField } from "../components/ui/Field";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { EXPERIENCE_LEVEL_LABELS } from "../lib/format";
import { applyServerErrors } from "../lib/forms";
import { findSampleJob, SAMPLE_JOBS, type SampleJob } from "../lib/sampleJobs";
import { splitSkillList } from "../lib/skills";
import { createJob } from "../services/jobs";
import type { ExperienceLevel } from "../types/api";

interface JobForm {
  title: string;
  company: string;
  experience_level: ExperienceLevel;
  description: string;
  required_skills: string;
  preferred_skills: string;
  auto_extract: boolean;
}

const LEVEL_OPTIONS = Object.entries(EXPERIENCE_LEVEL_LABELS).map(([value, label]) => ({ value, label }));

export function JobNewPage() {
  useDocumentTitle("Add job description");
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const resumeParam = params.get("resume");
  const [formError, setFormError] = useState<string | null>(null);
  const initialSample = findSampleJob(params.get("sample"));
  const [sampleTitle, setSampleTitle] = useState<string | null>(initialSample?.title ?? null);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<JobForm>({
    defaultValues: initialSample
      ? sampleValues(initialSample)
      : { title: "", company: "", experience_level: "unspecified", description: "", required_skills: "", preferred_skills: "", auto_extract: true },
  });

  function applySample(sample: SampleJob) {
    setFormError(null);
    reset(sampleValues(sample));
    setSampleTitle(sample.title);
  }

  async function onSubmit(values: JobForm) {
    setFormError(null);
    const required = splitSkillList(values.required_skills);
    const preferred = splitSkillList(values.preferred_skills);
    if (!values.description.trim() && required.length === 0 && preferred.length === 0) {
      setFormError("Paste a job description or list at least one required or preferred skill.");
      return;
    }
    try {
      const job = await createJob({
        title: values.title.trim(),
        company: values.company.trim(),
        experience_level: values.experience_level,
        description: values.description,
        required_skills: required,
        preferred_skills: preferred,
        auto_extract: values.auto_extract,
      });
      navigate(`/jobs/${job.id}${resumeParam ? `?resume=${encodeURIComponent(resumeParam)}` : ""}`, { state: { created: true } });
    } catch (err) {
      setFormError(
        applyServerErrors(err, setError, ["title", "company", "experience_level", "description", "required_skills", "preferred_skills"]),
      );
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Add a job description" description="You can review and edit every skill after saving." />
      <Card className="mb-4" title="No job description handy? Try a sample">
        <p className="mb-3 text-sm text-slate-600">
          These are example postings written for CareerForge, not real jobs. Pick one, then click <strong>Save job</strong>.
        </p>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_JOBS.map((sample) => (
            <Button key={sample.id} size="sm" variant="secondary" onClick={() => applySample(sample)}>
              {sample.title}
            </Button>
          ))}
        </div>
        {sampleTitle && (
          <p className="mt-3 text-sm text-emerald-800" role="status">
            Filled in “{sampleTitle}”. Review it below and click Save job.
          </p>
        )}
      </Card>
      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {formError && <Alert tone="error">{formError}</Alert>}
          <TextField
            label="Job title"
            required
            error={errors.title?.message}
            {...register("title", {
              required: "Enter the job title.",
              maxLength: { value: 200, message: "Use 200 characters or fewer." },
            })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Company" error={errors.company?.message} {...register("company", { maxLength: { value: 200, message: "Use 200 characters or fewer." } })} />
            <SelectField label="Experience level" options={LEVEL_OPTIONS} error={errors.experience_level?.message} {...register("experience_level")} />
          </div>
          <TextArea
            label="Job description"
            rows={10}
            hint="Paste the full posting. Lines under headings like “Nice to have” become preferred skills."
            error={errors.description?.message}
            {...register("description", { maxLength: { value: 20000, message: "Use 20,000 characters or fewer." } })}
          />
          <label className="flex items-center gap-2 text-sm text-slate-800">
            <input type="checkbox" className="h-4 w-4 rounded border-slate-300" {...register("auto_extract")} />
            Suggest skills from the description
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextArea
              label="Required skills (optional)"
              rows={3}
              hint="Comma or line separated, e.g. Python, Django, SQL"
              error={errors.required_skills?.message}
              {...register("required_skills")}
            />
            <TextArea
              label="Preferred skills (optional)"
              rows={3}
              hint="Nice-to-have skills"
              error={errors.preferred_skills?.message}
              {...register("preferred_skills")}
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" loading={isSubmitting}>
              Save job
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function sampleValues(sample: SampleJob): JobForm {
  return {
    title: sample.title,
    company: sample.company,
    experience_level: sample.experience_level,
    description: sample.description,
    required_skills: sample.required_skills.join(", "),
    preferred_skills: sample.preferred_skills.join(", "),
    // The skill lists are already exact; don't add extra suggestions from the text.
    auto_extract: false,
  };
}
