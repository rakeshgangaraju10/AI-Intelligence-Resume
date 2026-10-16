import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { applyServerErrors } from "../lib/forms";
import { requestPasswordReset } from "../services/auth";

interface ForgotForm {
  email: string;
}

export function ForgotPasswordPage() {
  useDocumentTitle("Forgot password");
  const [sentMessage, setSentMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ForgotForm>();

  async function onSubmit(values: ForgotForm) {
    setFormError(null);
    try {
      setSentMessage(await requestPasswordReset(values.email.trim()));
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ["email"]));
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold text-slate-900">Forgot your password?</h1>
      <p className="mt-1 text-sm text-slate-600">
        Enter the email you registered with and we'll send you a link to choose a new password.
      </p>
      {sentMessage ? (
        <div className="mt-6 space-y-4">
          <Alert tone="success" title="Check your email">
            {sentMessage} The link works once and expires in 1 hour.
          </Alert>
          <p className="text-sm">
            <Link to="/login" className="font-medium text-indigo-700 underline">
              Back to log in
            </Link>
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          {formError && <Alert tone="error">{formError}</Alert>}
          <TextField
            label="Email"
            type="email"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            autoComplete="email"
            required
            error={errors.email?.message}
            {...register("email", {
              required: "Enter your email address.",
              pattern: { value: /^\s*\S+@\S+\.\S+\s*$/, message: "Enter a valid email address." },
            })}
          />
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Send reset link
          </Button>
          <p className="text-center text-sm">
            <Link to="/login" className="font-medium text-indigo-700 underline">
              Back to log in
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
