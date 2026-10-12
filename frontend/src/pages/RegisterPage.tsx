import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { useAuth } from "../features/auth/AuthContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { applyServerErrors } from "../lib/forms";

interface RegisterForm {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export function RegisterPage() {
  useDocumentTitle("Create account");
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>();

  async function onSubmit(values: RegisterForm) {
    setFormError(null);
    try {
      await registerUser({ full_name: values.full_name.trim(), email: values.email.trim(), password: values.password });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ["full_name", "email", "password"]));
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
      <p className="mt-1 text-sm text-slate-600">
        Already registered?{" "}
        <Link to="/login" className="font-medium text-indigo-700 underline">
          Log in
        </Link>
      </p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        {formError && <Alert tone="error">{formError}</Alert>}
        <TextField
          label="Full name"
          autoComplete="name"
          required
          error={errors.full_name?.message}
          {...register("full_name", {
            required: "Enter your name.",
            maxLength: { value: 150, message: "Use 150 characters or fewer." },
          })}
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          error={errors.email?.message}
          {...register("email", {
            required: "Enter your email address.",
            pattern: { value: /^\S+@\S+\.\S+$/, message: "Enter a valid email address." },
          })}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          hint="At least 10 characters. Avoid common passwords and your name or email."
          error={errors.password?.message}
          {...register("password", {
            required: "Choose a password.",
            minLength: { value: 10, message: "Use at least 10 characters." },
          })}
        />
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          error={errors.confirm_password?.message}
          {...register("confirm_password", {
            required: "Re-enter your password.",
            validate: (value) => value === getValues("password") || "Passwords don't match.",
          })}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create account
        </Button>
      </form>
    </div>
  );
}
