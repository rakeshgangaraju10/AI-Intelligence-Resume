import { AxiosError } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { uploadResume } from "./resumes";
import * as wake from "./wake";

vi.mock("./wake", () => ({ wakeServer: vi.fn(), markServerMaybeAsleep: vi.fn() }));

const file = () => new File([new Uint8Array(10)], "cv.pdf", { type: "application/pdf" });
const RESUME = { id: "abc" };

afterEach(() => {
  vi.restoreAllMocks();
});

describe("uploadResume on a sleeping server", () => {
  it("wakes the server before uploading", async () => {
    vi.mocked(wake.wakeServer).mockResolvedValue(true);
    vi.spyOn(api, "get").mockResolvedValue({ data: null });
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: RESUME });
    await expect(uploadResume(file(), "CV")).resolves.toEqual(RESUME);
    expect(wake.wakeServer).toHaveBeenCalled();
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("retries once after a no-response failure once the server is awake", async () => {
    vi.mocked(wake.wakeServer).mockResolvedValue(true);
    vi.spyOn(api, "get").mockResolvedValue({ data: null });
    const post = vi
      .spyOn(api, "post")
      .mockRejectedValueOnce(new AxiosError("Network Error", "ERR_NETWORK"))
      .mockResolvedValueOnce({ data: RESUME });
    await expect(uploadResume(file(), "CV")).resolves.toEqual(RESUME);
    expect(post).toHaveBeenCalledTimes(2);
    expect(wake.markServerMaybeAsleep).toHaveBeenCalled();
    expect(wake.wakeServer).toHaveBeenLastCalledWith({ force: true });
  });

  it("does not retry validation errors", async () => {
    vi.mocked(wake.wakeServer).mockResolvedValue(true);
    vi.spyOn(api, "get").mockResolvedValue({ data: null });
    const config = {} as never;
    const response = {
      status: 400, statusText: "", headers: {}, config,
      data: { error: { code: "validation_error", message: "Bad file", fields: {} } },
    };
    const post = vi.spyOn(api, "post").mockRejectedValue(new AxiosError("Bad", "ERR_BAD_REQUEST", config, {}, response as never));
    await expect(uploadResume(file(), "CV")).rejects.toMatchObject({ status: 400 });
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("gives up with a clear message if the server never wakes", async () => {
    vi.mocked(wake.wakeServer).mockResolvedValueOnce(true).mockResolvedValueOnce(false);
    vi.spyOn(api, "get").mockResolvedValue({ data: null });
    vi.spyOn(api, "post").mockRejectedValue(new AxiosError("Network Error", "ERR_NETWORK"));
    await expect(uploadResume(file(), "CV")).rejects.toMatchObject({ code: "network_error" });
  });
});
