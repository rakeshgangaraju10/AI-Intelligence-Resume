import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "../features/auth/RouteGuards";
import { ApiError } from "../services/api";
import * as authApi from "../services/auth";
import { renderWithProviders } from "../test/utils";
import { LoginPage } from "./LoginPage";
import { RegisterPage } from "./RegisterPage";

vi.mock("../services/auth", () => ({
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}));

const mocked = vi.mocked(authApi);
const USER = { id: 1, email: "alex@example.com", full_name: "Alex Example", college_name: "Example College", graduation_year: 2025, date_joined: "2026-01-01T00:00:00Z" };

beforeEach(() => {
  mocked.fetchCurrentUser.mockResolvedValue(null);
});

describe("LoginPage", () => {
  it("validates required fields before calling the API", async () => {
    renderWithProviders(<LoginPage />, { route: "/login", path: "/login" });
    await userEvent.click(await screen.findByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Enter your email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(mocked.login).not.toHaveBeenCalled();
  });

  it("shows the server's generic credentials error", async () => {
    mocked.login.mockRejectedValue(
      new ApiError(400, "validation_error", "Invalid email or password.", {
        non_field_errors: [{ code: "invalid_credentials", message: "Invalid email or password." }],
      }),
    );
    renderWithProviders(<LoginPage />, { route: "/login", path: "/login" });
    await userEvent.type(await screen.findByLabelText(/email/i), "alex@example.com");
    await userEvent.type(screen.getByLabelText(/^password/i), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
  });

  it("logs in and goes to the dashboard", async () => {
    mocked.login.mockResolvedValue(USER);
    renderWithProviders(<LoginPage />, {
      route: "/login",
      path: "/login",
      extraRoutes: [{ path: "/dashboard", element: <p>Dashboard page</p> }],
    });
    await userEvent.type(await screen.findByLabelText(/email/i), "alex@example.com");
    await userEvent.type(screen.getByLabelText(/^password/i), "Correct-Horse-Battery-42");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Dashboard page")).toBeInTheDocument();
    expect(mocked.login).toHaveBeenCalledWith("alex@example.com", "Correct-Horse-Battery-42");
  });
});

describe("RegisterPage", () => {
  it("checks that the passwords match", async () => {
    renderWithProviders(<RegisterPage />, { route: "/register", path: "/register" });
    await userEvent.type(await screen.findByLabelText(/full name/i), "Casey Example");
    await userEvent.type(screen.getByLabelText(/^email/i), "casey@example.com");
    await userEvent.type(screen.getByLabelText(/^password/i), "Long-Enough-Pass-1");
    await userEvent.type(screen.getByLabelText(/confirm password/i), "Different-Pass-22");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Passwords don't match.")).toBeInTheDocument();
    expect(mocked.register).not.toHaveBeenCalled();
  });

  it("puts backend field errors next to the right field", async () => {
    mocked.register.mockRejectedValue(
      new ApiError(400, "validation_error", "An account with this email already exists.", {
        email: [{ code: "email_taken", message: "An account with this email already exists." }],
      }),
    );
    renderWithProviders(<RegisterPage />, { route: "/register", path: "/register" });
    await userEvent.type(await screen.findByLabelText(/full name/i), "Casey Example");
    await userEvent.type(screen.getByLabelText(/^email/i), "casey@example.com");
    await userEvent.type(screen.getByLabelText(/^password/i), "Long-Enough-Pass-1");
    await userEvent.type(screen.getByLabelText(/confirm password/i), "Long-Enough-Pass-1");
    await userEvent.type(screen.getByLabelText(/college name/i), "Example Institute of Technology");
    await userEvent.selectOptions(screen.getByLabelText(/year of passing out/i), "2025");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    const emailInput = screen.getByLabelText(/^email/i);
    await waitFor(() => expect(emailInput).toHaveAttribute("aria-invalid", "true"));
    expect(screen.getByText("An account with this email already exists.")).toBeInTheDocument();
  });
});

describe("RegisterPage college details", () => {
  it("requires college name and year of passing out", async () => {
    renderWithProviders(<RegisterPage />, { route: "/register", path: "/register" });
    await userEvent.type(await screen.findByLabelText(/full name/i), "Casey Example");
    await userEvent.type(screen.getByLabelText(/^email/i), "casey@example.com");
    await userEvent.type(screen.getByLabelText(/^password/i), "Long-Enough-Pass-1");
    await userEvent.type(screen.getByLabelText(/confirm password/i), "Long-Enough-Pass-1");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Enter your college name.")).toBeInTheDocument();
    expect(screen.getByText("Select your year of passing out.")).toBeInTheDocument();
    expect(mocked.register).not.toHaveBeenCalled();
  });

  it("sends them with the registration", async () => {
    mocked.register.mockResolvedValue(USER);
    renderWithProviders(<RegisterPage />, {
      route: "/register",
      path: "/register",
      extraRoutes: [{ path: "/dashboard", element: <p>Dashboard page</p> }],
    });
    await userEvent.type(await screen.findByLabelText(/full name/i), "Casey Example");
    await userEvent.type(screen.getByLabelText(/^email/i), "casey@example.com");
    await userEvent.type(screen.getByLabelText(/^password/i), "Long-Enough-Pass-1");
    await userEvent.type(screen.getByLabelText(/confirm password/i), "Long-Enough-Pass-1");
    await userEvent.type(screen.getByLabelText(/college name/i), "  Example Institute of Technology ");
    await userEvent.selectOptions(screen.getByLabelText(/year of passing out/i), "2025");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Dashboard page")).toBeInTheDocument();
    expect(mocked.register).toHaveBeenCalledWith({
      full_name: "Casey Example",
      email: "casey@example.com",
      password: "Long-Enough-Pass-1",
      college_name: "Example Institute of Technology",
      graduation_year: 2025,
    });
  });
});

describe("ProtectedRoute", () => {
  it("redirects signed-out users to the login page", async () => {
    renderWithProviders(<ProtectedRoute />, {
      route: "/dashboard",
      path: "/dashboard",
      extraRoutes: [{ path: "/login", element: <p>Login page</p> }],
    });
    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });
});
