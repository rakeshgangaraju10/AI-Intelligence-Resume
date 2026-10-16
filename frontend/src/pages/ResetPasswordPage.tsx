import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { applyServerErrors } from "../lib/forms";
import { ApiError } from "../services/api";
import { confirmPasswordReset } from "../services/auth";

interface ResetForm {
  new_password: string;
  confirm_password: string;
}

export function ResetPasswordPage() {
  useDocumentTitle("Choose a new password");
  const { uid = "", token = "" } = useParams();
  const [done, setDone] = useState<string | null>(null);
  const [linkInvalid, setLinkInvalid] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<ResetForm>();

  async function onSubmit(values: ResetForm) {
    setFormError(null);
    try {
      setDone(await confirmPasswordReset(uid, token, values.new_password));
    } catch (err) {
      if (err instanceof ApiError && err.fieldCode("token") === "invalid_token") {
        setLinkInvalid(true);
        return;
      }
      setFormError(applyServerErrors(err, setError, ["new_password"]));
    }
  }

  if (done) {
    return (
      <div className="mx-auto max-w-md space-y-4 px-4 py-16">
        <Alert tone="success" title="Password changed">
          {done}
        </Alert>
        <Link to="/login" className="font-medium text-indigo-700 underline">
          Go to log in
        </Link>
      </div>
    );
  }

  if (linkInvalid) {
    return (
      <div className="mx-auto max-w-md space-y-4 px-4 py-16">
        <Alert tone="error" title="This link can't be used">
          Reset links work once and expire after 1 hour.
        </Alert>
        <Link to="/forgot-password" className="font-medium text-indigo-700 underline">
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold text-slate-900">Choose a new password</h1>
      <p className="mt-1 text-sm text-slate-600">At least 10 characters; not a common password or only numbers.</p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        {formError && <Alert tone="error">{formError}</Alert>}
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          required
          error={errors.new_password?.message}
          {...register("new_password", {
            required: "Enter a new password.",
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
            required: "Type the new password again.",
            validate: (value) => value === getValues("new_password") || "Passwords don't match.",
          })}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Save new password
        </Button>
      </form>
    </div>
  );
}
