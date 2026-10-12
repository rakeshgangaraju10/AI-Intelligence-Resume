import { Badge } from "../../components/ui/Feedback";
import type { EntrySource } from "../../types/api";

/** Shows whether data was detected by the parser (and confirmed or not) or added by the user. */
export function SourceBadge({ source, verified }: { source: EntrySource; verified: boolean }) {
  if (source === "user") return <Badge tone="sky">Added by you</Badge>;
  if (verified) return <Badge tone="green">Confirmed</Badge>;
  return <Badge tone="amber">Detected · please review</Badge>;
}
