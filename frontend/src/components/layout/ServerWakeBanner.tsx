import { useServerWaking } from "../../services/wake";

/** Shown while the free-plan server is waking up, so a slow first load doesn't look broken. */
export function ServerWakeBanner() {
  const waking = useServerWaking();
  if (!waking) return null;
  return (
    <div role="status" className="bg-sky-100 px-4 py-2 text-center text-sm text-sky-900 print:hidden">
      Starting the server… this can take up to a minute after it has been idle. Please wait.
    </div>
  );
}
