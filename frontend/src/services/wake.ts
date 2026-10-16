/**
 * Free hosting sleeps after ~15 idle minutes and takes up to a minute to wake.
 * `wakeServer()` pings the health endpoint (one request at a time, shared by all
 * callers) and reports "waking" to the UI if it takes more than a moment.
 */
import { useSyncExternalStore } from "react";

import { api } from "./api";

type WakeState = "idle" | "waking";

const SLOW_AFTER_MS = 2500;
const WAKE_TIMEOUT_MS = 100_000;
const AWAKE_FOR_MS = 5 * 60_000; // assume still awake for 5 minutes after a successful ping

let state: WakeState = "idle";
let pending: Promise<boolean> | null = null;
let lastAwakeAt = 0;
const listeners = new Set<() => void>();

function setState(next: WakeState) {
  if (state === next) return;
  state = next;
  listeners.forEach((l) => l());
}

/** Resolve true once the server answers (false if it never does). */
export function wakeServer({ force = false } = {}): Promise<boolean> {
  if (!force && Date.now() - lastAwakeAt < AWAKE_FOR_MS) return Promise.resolve(true);
  if (pending) return pending;
  const slowTimer = setTimeout(() => setState("waking"), SLOW_AFTER_MS);
  pending = api
    .get("/health/", { timeout: WAKE_TIMEOUT_MS })
    .then(() => {
      lastAwakeAt = Date.now();
      return true;
    })
    .catch(() => false)
    .finally(() => {
      clearTimeout(slowTimer);
      setState("idle");
      pending = null;
    });
  return pending;
}

/** Call after a request failed without a response, so the next ping isn't skipped. */
export function markServerMaybeAsleep(): void {
  lastAwakeAt = 0;
}

export function useServerWaking(): boolean {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => state === "waking",
  );
}

/** Ping on load and whenever the user comes back to a tab that was hidden for a while. */
export function startWakeOnReturn(): () => void {
  void wakeServer();
  let hiddenAt = 0;
  const onVisibility = () => {
    if (document.visibilityState === "hidden") hiddenAt = Date.now();
    else if (hiddenAt && Date.now() - hiddenAt > 60_000) void wakeServer({ force: true });
  };
  document.addEventListener("visibilitychange", onVisibility);
  return () => document.removeEventListener("visibilitychange", onVisibility);
}
