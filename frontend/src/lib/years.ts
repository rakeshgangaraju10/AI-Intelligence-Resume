/** Year-of-passing-out choices: a few years ahead (current students) back to 1980. */
export function graduationYearOptions(now: Date = new Date()): { value: string; label: string }[] {
  const latest = now.getFullYear() + 6;
  const years: { value: string; label: string }[] = [];
  for (let year = latest; year >= 1980; year -= 1) years.push({ value: String(year), label: String(year) });
  return years;
}
