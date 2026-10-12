/**
 * Shown only in public demo builds (VITE_DEMO_MODE=true at build time), so
 * visitors don't upload real personal resumes to a demo server.
 */
export function DemoBanner() {
  if (import.meta.env.VITE_DEMO_MODE !== "true") return null;
  return (
    <div role="note" className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900 print:hidden">
      Public demo: please upload a sample resume, not your real one. Demo data may be deleted at any time.
    </div>
  );
}
