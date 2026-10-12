/** Split "Python, Django\nSQL" into unique, trimmed skill names (case-insensitive de-duplication). */
export function splitSkillList(text: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of text.split(/[,\n]/)) {
    const name = raw.replace(/\s+/g, " ").trim();
    if (name && !seen.has(name.toLowerCase())) {
      seen.add(name.toLowerCase());
      result.push(name.slice(0, 100));
    }
  }
  return result;
}
