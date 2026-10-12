/** Colour-coded score pill. Colour is never the only signal: the number is always shown. */
export function ScoreBadge({ score }: { score: number }) {
  const tone =
    score >= 75 ? "bg-emerald-100 text-emerald-800" : score >= 50 ? "bg-amber-100 text-amber-900" : "bg-red-100 text-red-800";
  return (
    <span className={`inline-flex min-w-[3.5rem] justify-center rounded-md px-2 py-1 text-sm font-semibold ${tone}`}>
      {score.toFixed(1)}
    </span>
  );
}
