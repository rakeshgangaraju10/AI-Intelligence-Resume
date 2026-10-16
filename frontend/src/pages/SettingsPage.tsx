import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert, Card, PageHeader } from "../components/ui/Feedback";
import { SelectField, TextField } from "../components/ui/Field";
import { useAuth } from "../features/auth/AuthContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDate } from "../lib/format";
import { applyServerErrors } from "../lib/forms";
import { graduationYearOptions } from "../lib/years";
import { changePassword, deleteAccount, updateProfile } from "../services/auth";

interface ProfileForm {
  full_name: string;
  college_name: string;
  graduation_year: string;
}

const PROFILE_YEAR_OPTIONS = [{ value: "", label: "Select year" }, ...graduationYearOptions()];

function ProfileSection() {
  const { user, setUser } = useAuth();
  const [status, setStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileForm>({
    values: {
      full_name: user?.full_name ?? "",
      college_name: user?.college_name ?? "",
      graduation_year: user?.graduation_year ? String(user.graduation_year) : "",
    },
  });

  async function onSubmit(values: ProfileForm) {
    setStatus(null);
    try {
      setUser(
        await updateProfile({
          full_name: values.full_name.trim(),
          college_name: values.college_name.trim(),
          graduation_year: Number(values.graduation_year),
        }),
      );
      setStatus({ tone: "success", text: "Profile updated." });
    } catch (err) {
      const message = applyServerErrors(err, setError, ["full_name", "college_name", "graduation_year"]);
      if (message) setStatus({ tone: "error", text: message });
    }
  }

  return (
    <Card title="Profile">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {status && <Alert tone={status.tone}>{status.text}</Alert>}
        <TextField label="Email" value={user?.email ?? ""} disabled hint="Your sign-in email can't be changed here." />
        <TextField
          label="Full name"
          required
          error={errors.full_name?.message}
          {...register("full_name", {
            required: "Enter your name.",
            maxLength: { value: 150, message: "Use 150 characters or fewer." },
          })}
        />
        <TextField
          label="College name"
          required
          error={errors.college_name?.message}
          {...register("college_name", {
            required: "Enter your college name.",
            validate: (value) => value.trim().length >= 2 || "Enter your college name.",
            maxLength: { value: 200, message: "Use 200 characters or fewer." },
          })}
        />
        <SelectField
          label="Year of passing out"
          required
          options={PROFILE_YEAR_OPTIONS}
          error={errors.graduation_year?.message}
          {...register("graduation_year", { required: "Select your year of passing out." })}
        />
        {user && <p className="text-xs text-slate-500">Member since {formatDate(user.date_joined)}</p>}
        <Button type="submit" loading={isSubmitting}>
          Save profile
        </Button>
      </form>
    </Card>
  );
}

interface PasswordForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

function PasswordSection() {
  const [status, setStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<PasswordForm>();

  async function onSubmit(values: PasswordForm) {
    setStatus(null);
    try {
      await changePassword(values.current_password, values.new_password);
      reset();
      setStatus({ tone: "success", text: "Password changed. Other signed-in sessions have been logged out." });
    } catch (err) {
      const message = applyServerErrors(err, setError, ["current_password", "new_password"]);
      if (message) setStatus({ tone: "error", text: message });
    }
  }

  return (
    <Card title="Change password">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {status && <Alert tone={status.tone}>{status.text}</Alert>}
        <TextField
          label="Current password"
          type="password"
          autoComplete="current-password"
          required
          error={errors.current_password?.message}
          {...register("current_password", { required: "Enter your current password." })}
        />
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          required
          hint="At least 10 characters."
          error={errors.new_password?.message}
          {...register("new_password", {
            required: "Choose a new password.",
            minLength: { value: 10, message: "Use at least 10 characters." },
          })}
        />
        <TextField
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          required
          error={errors.confirm_password?.message}
          {...register("confirm_password", {
            required: "Re-enter the new password.",
            validate: (value) => value === getValues("new_password") || "Passwords don't match.",
          })}
        />
        <Button type="submit" loading={isSubmitting}>
          Change password
        </Button>
      </form>
    </Card>
  );
}

function DangerZone() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<{ password: string }>();

  async function onSubmit(values: { password: string }) {
    if (!window.confirm("Permanently delete your account, all resumes, job descriptions and analyses? This cannot be undone.")) return;
    setFormError(null);
    try {
      await deleteAccount(values.password);
      setUser(null);
      navigate("/", { replace: true });
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ["password"]));
    }
  }

  return (
    <Card title="Delete account" className="border-red-200">
      <p className="mb-4 text-sm text-slate-700">
        This permanently deletes your account, every uploaded resume file, all extracted data, saved job descriptions and
        analyses. To delete individual resumes instead, use the Resumes page.
      </p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {formError && <Alert tone="error">{formError}</Alert>}
        <TextField
          label="Confirm with your password"
          type="password"
          autoComplete="current-password"
          required
          error={errors.password?.message}
          {...register("password", { required: "Enter your password to confirm." })}
        />
        <Button type="submit" variant="danger" loading={isSubmitting}>
          Delete my account
        </Button>
      </form>
    </Card>
  );
}

export function SettingsPage() {
  useDocumentTitle("Settings");
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader title="Settings" description="Manage your profile, password and data." />
      <ProfileSection />
      <PasswordSection />
      <Card title="Your data">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          <li>Resume PDFs are stored privately and are never served from a public link.</li>
          <li>Your resume text is not sent to any external AI service; all analysis runs on CareerForge's own server.</li>
          <li>Deleting a resume removes the file, its extracted data and the analyses that used it.</li>
        </ul>
      </Card>
      <DangerZone />
    </div>
  );
}
