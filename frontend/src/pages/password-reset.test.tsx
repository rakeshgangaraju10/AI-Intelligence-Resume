import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/api";
import * as authApi from "../services/auth";
import { renderWithProviders } from "../test/utils";
import { ForgotPasswordPage } from "./ForgotPasswordPage";
import { LoginPage } from "./LoginPage";
import { ResetPasswordPage } from "./ResetPasswordPage";

vi.mock("../services/auth", () => ({
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

const mocked = vi.mocked(authApi);
const SENT = "If an account exists for that email, we've sent a link to reset the password. Check your inbox and spam folder.";

beforeEach(() => {
  mocked.fetchCurrentUser.mockResolvedValue(null);
});

describe("Forgot password", () => {
  it("is linked from the login page", async () => {
    renderWithProviders(<LoginPage />, { route: "/login", path: "/login" });
    expect(await screen.findByRole("link", { name: "Forgot password?" })).toHaveAttribute("href", "/forgot-password");
  });

  it("sends the email and shows the same neutral message for any address", async () => {
    mocked.requestPasswordReset.mockResolvedValue(SENT);
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password", path: "/forgot-password" });
    await userEvent.type(await screen.findByLabelText(/email/i), "alex@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByText(/If an account exists for that email/)).toBeInTheDocument();
    expect(screen.getByText(/expires in 1 hour/)).toBeInTheDocument();
    expect(mocked.requestPasswordReset).toHaveBeenCalledWith("alex@example.com");
  });

  it("validates the email before calling the API", async () => {
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password", path: "/forgot-password" });
    await userEvent.click(await screen.findByRole("button", { name: "Send reset link" }));
    expect(await screen.findByText("Enter your email address.")).toBeInTheDocument();
    expect(mocked.requestPasswordReset).not.toHaveBeenCalled();
  });

  it("shows the rate-limit message", async () => {
    mocked.requestPasswordReset.mockRejectedValue(new ApiError(429, "throttled", "Too many requests. Try again later."));
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password", path: "/forgot-password" });
    await userEvent.type(await screen.findByLabelText(/email/i), "alex@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests");
  });
});

describe("Reset password", () => {
  const route = { route: "/reset-password/MQ/abc-123", path: "/reset-password/:uid/:token" };

  it("sets the new password using the link's uid and token", async () => {
    mocked.confirmPasswordReset.mockResolvedValue("Your password has been changed. You can now log in.");
    renderWithProviders(<ResetPasswordPage />, route);
    await userEvent.type(await screen.findByLabelText(/^new password/i), "Brand-New-Secret-77");
    await userEvent.type(screen.getByLabelText(/confirm new password/i), "Brand-New-Secret-77");
    await userEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("Password changed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to log in" })).toBeInTheDocument();
    expect(mocked.confirmPasswordReset).toHaveBeenCalledWith("MQ", "abc-123", "Brand-New-Secret-77");
  });

  it("checks the two passwords match", async () => {
    renderWithProviders(<ResetPasswordPage />, route);
    await userEvent.type(await screen.findByLabelText(/^new password/i), "Brand-New-Secret-77");
    await userEvent.type(screen.getByLabelText(/confirm new password/i), "Different-Secret-88");
    await userEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("Passwords don't match.")).toBeInTheDocument();
    expect(mocked.confirmPasswordReset).not.toHaveBeenCalled();
  });

  it("explains an expired or used link and offers a new one", async () => {
    mocked.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, "validation_error", "x", {
        token: [{ code: "invalid_token", message: "This reset link is invalid or has expired. Request a new one." }],
      }),
    );
    renderWithProviders(<ResetPasswordPage />, route);
    await userEvent.type(await screen.findByLabelText(/^new password/i), "Brand-New-Secret-77");
    await userEvent.type(screen.getByLabelText(/confirm new password/i), "Brand-New-Secret-77");
    await userEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("This link can't be used")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Request a new link" })).toHaveAttribute("href", "/forgot-password");
  });

  it("shows the server's password rule next to the field", async () => {
    mocked.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, "validation_error", "x", {
        new_password: [{ code: "password_too_common", message: "This password is too common." }],
      }),
    );
    renderWithProviders(<ResetPasswordPage />, route);
    await userEvent.type(await screen.findByLabelText(/^new password/i), "Password1234");
    await userEvent.type(screen.getByLabelText(/confirm new password/i), "Password1234");
    await userEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("This password is too common.")).toBeInTheDocument();
  });
});
