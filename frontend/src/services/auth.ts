import type { User } from "../types/api";
import { api, ApiError, ensureCsrfCookie, request, resetCsrf } from "./api";

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
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

export function updateProfile(fullName: string): Promise<User> {
  return request(() => api.patch<User>("/auth/me/", { full_name: fullName }));
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
