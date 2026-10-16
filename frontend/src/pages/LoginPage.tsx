import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router";

import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Feedback";
import { TextField } from "../components/ui/Field";
import { useAuth } from "../features/auth/AuthContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { applyServerErrors } from "../lib/forms";

interface LoginForm {
  email: string;
  password: string;
}

export function LoginPage() {
  useDocumentTitle("Log in");
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>();

  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  async function onSubmit(values: LoginForm) {
    setFormError(null);
    try {
      await login(values.email.trim(), values.password);
      navigate(from, { replace: true });
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ["email", "password"]));
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold text-slate-900">Log in</h1>
      <p className="mt-1 text-sm text-slate-600">
        New here?{" "}
        <Link to="/register" className="font-medium text-indigo-700 underline">
          Create an account
        </Link>
      </p>
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
        <TextField
          label="Password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          required
          error={errors.password?.message}
          {...register("password", { required: "Enter your password." })}
        />
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300"
            checked={showPassword}
            onChange={(e) => setShowPassword(e.target.checked)}
          />
          Show password
        </label>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Log in
        </Button>
        <p className="text-center text-sm">
          <Link to="/forgot-password" className="font-medium text-indigo-700 underline">
            Forgot password?
          </Link>
        </p>
      </form>
    </div>
  );
}
