"""
Deterministic skill matching against a dictionary of canonical skills + aliases.

Pure Python (no Django imports) so it can be unit-tested in isolation.

Matching rules
--------------
* Whole-token matching: an alias must not be glued to surrounding letters or
  digits, so "Java" does not match inside "JavaScript" and "Go" not inside "Google".
* Longest alias wins at a position: "Node.js" beats "Node", "C++" beats "C",
  "Spring Boot" beats "Spring".
* Ordinary aliases match case-insensitively anywhere.
* Ambiguous aliases (letters or everyday words such as "C", "R", "Go", "Excel")
  match only when `allow_ambiguous=True` (callers pass this for a resume's
  Skills section or an explicit skills list), case-sensitively and with stricter
  boundaries.
* Internal whitespace in multi-word aliases is flexible ("Spring  Boot").
"""
import re
from collections.abc import Iterable
from dataclasses import dataclass

# Characters that may not touch an alias for it to count as a separate token.
_TOKEN_CHARS = r"A-Za-z0-9_+#"
_STRICT_CHARS = r"A-Za-z0-9_+#&\-./'"


@dataclass(frozen=True)
class AliasEntry:
    alias: str
    skill_name: str
    is_ambiguous: bool = False


@dataclass(frozen=True)
class SkillMatch:
    skill_name: str
    matched_text: str
    start: int
    end: int


def _alias_pattern(alias: str) -> str:
    return r"\s+".join(re.escape(part) for part in alias.split())


def _compile(aliases: list[str], boundary_chars: str, flags: int) -> re.Pattern | None:
    if not aliases:
        return None
    ordered = sorted(set(aliases), key=len, reverse=True)
    alternation = "|".join(_alias_pattern(a) for a in ordered)
    return re.compile(
        rf"(?<![{boundary_chars}])(?:{alternation})(?![{boundary_chars}])", flags
    )


class SkillDictionary:
    def __init__(self, entries: Iterable[AliasEntry]) -> None:
        self._by_lower: dict[str, AliasEntry] = {}
        for entry in entries:
            alias = " ".join(entry.alias.split())
            if alias:
                self._by_lower.setdefault(alias.lower(), AliasEntry(alias, entry.skill_name, entry.is_ambiguous))

        regular = [e.alias for e in self._by_lower.values() if not e.is_ambiguous]
        ambiguous = [e.alias for e in self._by_lower.values() if e.is_ambiguous]
        self._regular = _compile(regular, _TOKEN_CHARS, re.IGNORECASE)
        self._ambiguous = _compile(ambiguous, _STRICT_CHARS, 0)
        self._ambiguous_exact = {e.alias: e for e in self._by_lower.values() if e.is_ambiguous}

    def __len__(self) -> int:
        return len(self._by_lower)

    @property
    def skill_names(self) -> set[str]:
        return {e.skill_name for e in self._by_lower.values()}

    def resolve(self, name: str) -> str | None:
        """Exact (case-insensitive) alias lookup for explicit user/job input."""
        entry = self._by_lower.get(" ".join(name.split()).lower())
        return entry.skill_name if entry else None

    def find(self, text: str, *, allow_ambiguous: bool = False) -> list[SkillMatch]:
        """All non-overlapping skill mentions in `text`, in order of appearance."""
        matches: list[SkillMatch] = []
        taken: list[tuple[int, int]] = []

        if self._regular is not None:
            for m in self._regular.finditer(text):
                entry = self._by_lower[" ".join(m.group(0).split()).lower()]
                matches.append(SkillMatch(entry.skill_name, m.group(0), m.start(), m.end()))
                taken.append((m.start(), m.end()))

        if allow_ambiguous and self._ambiguous is not None:
            for m in self._ambiguous.finditer(text):
                if any(s < m.end() and m.start() < e for s, e in taken):
                    continue  # already covered by a longer, unambiguous alias
                entry = self._ambiguous_exact.get(" ".join(m.group(0).split()))
                if entry is not None:
                    matches.append(SkillMatch(entry.skill_name, m.group(0), m.start(), m.end()))

        matches.sort(key=lambda s: s.start)
        return matches
