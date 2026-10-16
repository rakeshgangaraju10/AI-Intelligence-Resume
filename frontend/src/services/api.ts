import axios, { AxiosError } from "axios";

import type { ApiErrorBody, FieldError } from "../types/api";

/**
 * Shared HTTP client.
 *
 * Auth is a Django session cookie (HttpOnly; JavaScript never sees it). Unsafe
 * requests carry the CSRF token: axios copies the `csrftoken` cookie into the
 * `X-CSRFToken` header automatically for same-origin requests. In development
 * Vite proxies /api to Django, so the app and API share one origin.
 */
export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: { Accept: "application/json" },
  timeout: 60_000,
});

/** A normalised API error the UI can render without knowing about axios. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, FieldError[]>;

  constructor(status: number, code: string, message: string, fields: Record<string, FieldError[]> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }

  /** First message for a field, if the server rejected it. */
  fieldMessage(field: string): string | undefined {
    return this.fields[field]?.[0]?.message;
  }

  /** First code for a field (e.g. "pdf_encrypted"). */
  fieldCode(field: string): string | undefined {
    return this.fields[field]?.[0]?.code;
  }
}

function isApiErrorBody(data: unknown): data is ApiErrorBody {
  return (
    typeof data === "object" &&
    data !== null &&
    "error" in data &&
    typeof (data as ApiErrorBody).error?.message === "string"
  );
}

/** Convert anything thrown by axios (or otherwise) into an ApiError. */
export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (err instanceof AxiosError) {
    if (!err.response) {
      if (err.code === "ECONNABORTED" || err.code === "ETIMEDOUT") {
        return new ApiError(
          0,
          "timeout",
          "The server took too long to answer. It may have been starting up; please try again.",
        );
      }
      return new ApiError(
        0,
        "network_error",
        "Can't reach the server right now. It may be starting up (up to a minute) or your connection dropped; please try again.",
      );
    }
    const { status, data } = err.response;
    if (isApiErrorBody(data)) {
      return new ApiError(status, data.error.code, data.error.message, data.error.fields ?? {});
    }
    if (status === 404) return new ApiError(404, "not_found", "Not found.");
    return new ApiError(status, "server_error", "Something went wrong on our side. Please try again.");
  }
  return new ApiError(0, "unknown_error", "Something went wrong. Please try again.");
}

function hasCsrfCookie(): boolean {
  return document.cookie.split(";").some((c) => c.trim().startsWith("csrftoken="));
}

const UNSAFE_METHODS = new Set(["post", "put", "patch", "delete"]);

// Before any unsafe request, make sure the CSRF cookie exists (e.g. first visit,
// or the user cleared cookies) so Django's CSRF check can pass.
api.interceptors.request.use(async (config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (UNSAFE_METHODS.has(method) && !hasCsrfCookie()) {
    await ensureCsrfCookie();
  }
  return config;
});

/** Make sure the CSRF cookie exists before the first unsafe request. */
let csrfReady: Promise<void> | null = null;
export function ensureCsrfCookie(): Promise<void> {
  if (csrfReady) return csrfReady;
  const pending = api
    .get("/auth/csrf/")
    .then(() => undefined)
    .catch((err: unknown) => {
      csrfReady = null; // allow a retry after a failure
      throw toApiError(err);
    });
  csrfReady = pending;
  return pending;
}

/** Call after login/logout: Django rotates the CSRF token on login. */
export function resetCsrf(): void {
  csrfReady = null;
}

/** Run a request and rethrow failures as ApiError. */
export async function request<T>(fn: () => Promise<{ data: T }>): Promise<T> {
  try {
    const response = await fn();
    return response.data;
  } catch (err) {
    throw toApiError(err);
  }
}
