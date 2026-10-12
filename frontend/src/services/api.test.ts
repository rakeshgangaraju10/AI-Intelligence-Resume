import { AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";
import { describe, expect, it } from "vitest";

import { ApiError, toApiError } from "./api";

function axiosErrorWith(status: number, data: unknown): AxiosError {
  const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig;
  const response = { status, data, statusText: "", headers: {}, config } as AxiosResponse;
  return new AxiosError("Request failed", "ERR_BAD_REQUEST", config, {}, response);
}

describe("toApiError", () => {
  it("reads the backend error envelope including field errors", () => {
    const err = toApiError(
      axiosErrorWith(400, {
        error: {
          code: "validation_error",
          message: "The PDF is password-protected.",
          fields: { file: [{ code: "pdf_encrypted", message: "The PDF is password-protected." }] },
        },
      }),
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(400);
    expect(err.code).toBe("validation_error");
    expect(err.fieldCode("file")).toBe("pdf_encrypted");
    expect(err.fieldMessage("file")).toBe("The PDF is password-protected.");
    expect(err.fieldMessage("title")).toBeUndefined();
  });

  it("gives a friendly message when the server is unreachable", () => {
    const err = toApiError(new AxiosError("Network Error", "ERR_NETWORK"));
    expect(err.status).toBe(0);
    expect(err.code).toBe("network_error");
    expect(err.message).toMatch(/can't reach the server/i);
  });

  it("never exposes raw HTML or stack traces from unexpected responses", () => {
    const err = toApiError(axiosErrorWith(500, "<html>Traceback ...</html>"));
    expect(err.code).toBe("server_error");
    expect(err.message).not.toMatch(/Traceback/);
  });

  it("maps a bare 404 to not_found", () => {
    expect(toApiError(axiosErrorWith(404, "")).code).toBe("not_found");
  });

  it("passes ApiError through unchanged and wraps unknown values", () => {
    const original = new ApiError(403, "permission_denied", "Nope");
    expect(toApiError(original)).toBe(original);
    expect(toApiError("boom").code).toBe("unknown_error");
  });
});
