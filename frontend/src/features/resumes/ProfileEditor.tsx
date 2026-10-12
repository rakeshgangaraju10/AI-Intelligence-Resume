import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "../../components/ui/Button";
import { Alert, Badge, Card } from "../../components/ui/Feedback";
import { TextArea, TextField } from "../../components/ui/Field";
import { applyServerErrors } from "../../lib/forms";
import { updateProfile } from "../../services/resumes";
import type { ResumeProfile } from "../../types/api";

interface ProfileForm {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  links: string;
  summary: string;
}

function toForm(profile: ResumeProfile | null): ProfileForm {
  return {
    full_name: profile?.full_name ?? "",
    email: profile?.email ?? "",
    phone: profile?.phone ?? "",
    location: profile?.location ?? "",
    links: (profile?.links ?? []).join("\n"),
    summary: profile?.summary ?? "",
  };
}

export function ProfileEditor({ resumeId, profile, onSaved }: { resumeId: string; profile: ResumeProfile | null; onSaved: (p: ResumeProfile) => void }) {
  const [editing, setEditing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileForm>({ values: toForm(profile) });

  async function onSubmit(values: ProfileForm) {
    setFormError(null);
    try {
      const saved = await updateProfile(resumeId, {
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim(),
        location: values.location.trim(),
        links: values.links.split("\n").map((l) => l.trim()).filter(Boolean),
        summary: values.summary.trim(),
      });
      onSaved(saved);
      setEditing(false);
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ["full_name", "email", "phone", "location", "links", "summary"]));
    }
  }

  const empty = "Not found in resume";

  return (
    <Card
      title="Contact information & summary"
      actions={
        <>
          {profile?.user_edited ? <Badge tone="sky">Edited by you</Badge> : <Badge tone="amber">Detected · please review</Badge>}
          {!editing && (
            <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
              Edit
            </Button>
          )}
        </>
      }
    >
      {editing ? (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {formError && <Alert tone="error">{formError}</Alert>}
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Full name" error={errors.full_name?.message} {...register("full_name", { maxLength: { value: 150, message: "Use 150 characters or fewer." } })} />
            <TextField label="Email" type="email" error={errors.email?.message} {...register("email")} />
            <TextField label="Phone" error={errors.phone?.message} {...register("phone", { maxLength: { value: 30, message: "Use 30 characters or fewer." } })} />
            <TextField label="Location" error={errors.location?.message} {...register("location", { maxLength: { value: 120, message: "Use 120 characters or fewer." } })} />
          </div>
          <TextArea label="Links" hint="One per line (LinkedIn, GitHub, portfolio). Up to 10." rows={3} error={errors.links?.message} {...register("links")} />
          <TextArea label="Professional summary" rows={4} error={errors.summary?.message} {...register("summary")} />
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                reset(toForm(profile));
                setEditing(false);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              Save
            </Button>
          </div>
        </form>
      ) : (
        <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          {(
            [
              ["Name", profile?.full_name],
              ["Email", profile?.email],
              ["Phone", profile?.phone],
              ["Location", profile?.location],
            ] as const
          ).map(([label, value]) => (
            <div key={label}>
              <dt className="text-slate-500">{label}</dt>
              <dd className={value ? "text-slate-900" : "italic text-slate-400"}>{value || empty}</dd>
            </div>
          ))}
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Links</dt>
            <dd className={profile?.links.length ? "text-slate-900" : "italic text-slate-400"}>
              {profile?.links.length ? profile.links.join(" · ") : empty}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Summary</dt>
            <dd className={profile?.summary ? "whitespace-pre-line text-slate-900" : "italic text-slate-400"}>{profile?.summary || empty}</dd>
          </div>
        </dl>
      )}
    </Card>
  );
}
