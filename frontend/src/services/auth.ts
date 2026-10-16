import type { User } from "../types/api";
import { api, ApiError, ensureCsrfCookie, request, resetCsrf } from "./api";

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  college_name: string;
  graduation_year: number;
}

export interface ProfileUpdate {
  full_name: string;
  college_name: string;
  graduation_year: number;
}

export async function fetchCurrentUser(): Promise<User | null> {
  try {
    return await request(() => api.get<User>("/auth/me/"));
  } catch (err) {
    // 401/403 simply means "not logged in".
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) return null;
    throw err;
  }
}

export async function login(email: string, password: string): Promise<User> {
  await ensureCsrfCookie();
  const user = await request(() => api.post<User>("/auth/login/", { email, password }));
  resetCsrf();
  return user;
}

export async function register(payload: RegisterPayload): Promise<User> {
  await ensureCsrfCookie();
  const user = await request(() => api.post<User>("/auth/register/", payload));
  resetCsrf();
  return user;
}

export async function logout(): Promise<void> {
  await ensureCsrfCookie();
  await request(() => api.post("/auth/logout/"));
  resetCsrf();
}

export function updateProfile(data: ProfileUpdate): Promise<User> {
  return request(() => api.patch<User>("/auth/me/", data));
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return request(() =>
    api.post("/auth/change-password/", { current_password: currentPassword, new_password: newPassword }),
  ).then(() => undefined);
}

export function deleteAccount(password: string): Promise<void> {
  return request(() => api.delete("/auth/me/", { data: { password } })).then(() => {
    resetCsrf();
  });
}

/** Ask for a reset link. The server answers the same way whether or not the email has an account. */
export async function requestPasswordReset(email: string): Promise<string> {
  await ensureCsrfCookie();
  const data = await request(() => api.post<{ detail: string }>("/auth/password-reset/", { email }));
  return data.detail;
}

/** Set a new password using the uid/token from the emailed link. */
export async function confirmPasswordReset(uid: string, token: string, newPassword: string): Promise<string> {
  await ensureCsrfCookie();
  const data = await request(() =>
    api.post<{ detail: string }>("/auth/password-reset/confirm/", { uid, token, new_password: newPassword }),
  );
  return data.detail;
}
