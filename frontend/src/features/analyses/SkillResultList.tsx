import { Badge } from "../../components/ui/Feedback";
import type { SkillResult } from "../../types/api";

const STATUS_BADGE = {
  matched: <Badge tone="green">Matched</Badge>,
  missing: <Badge tone="red">Missing</Badge>,
  related: <Badge tone="amber">Related skill found</Badge>,
} as const;

export function SkillResultList({ results, emptyText }: { results: SkillResult[]; emptyText: string }) {
  if (results.length === 0) return <p className="text-sm text-slate-600">{emptyText}</p>;
  return (
    <ul className="space-y-3">
      {results.map((r) => (
        <li key={r.skill_name} className="rounded-md border border-slate-200 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-slate-900">{r.skill_name}</span>
            {STATUS_BADGE[r.status]}
            {r.weight > 1 && <Badge>weight {r.weight}</Badge>}
          </div>
          <p className="mt-1 text-sm text-slate-700">{r.explanation}</p>
          {r.evidence.length > 0 && (
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer text-indigo-700">Evidence from your resume ({r.evidence.length})</summary>
              <ul className="mt-2 space-y-1">
                {r.evidence.map((e, i) => (
                  <li key={`${e.location}-${i}`} className="rounded bg-slate-50 px-2 py-1 text-xs text-slate-700">
                    <span className="font-medium">{e.location}:</span> <q>{e.text}</q>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </li>
      ))}
    </ul>
  );
}
