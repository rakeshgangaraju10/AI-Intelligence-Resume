# Matching algorithm (`baseline-v1`)

CareerForge compares a resume with a job using a deterministic, rule-based
engine (`backend/apps/analyses/services/matching.py`). The same inputs always
produce the same output, and every result carries a written reason.

> The score is a **resume-to-job matching score**: the weighted share of the
> job's listed skills that appear in the resume. It is **not** a probability of
> being shortlisted or hired, and the API labels it that way.

## Inputs

| Input | Source |
|---|---|
| Job requirements | `JobRequirement` rows: canonical skill name, `kind` (required / preferred), `weight` 1–5. Suggested from the pasted description, then reviewed and edited by the user. |
| Resume skills | `ResumeSkill` rows (parser-detected or user-added) plus skills mentioned in the resume's project, experience and certification entries. |
| Evidence | For each resume skill: the Skills-section line, and the project / experience / certification text that mentions it. |
| Related-skill groups | Admin-curated `SkillGroup`s, e.g. *relational SQL databases* = PostgreSQL, MySQL, SQLite, SQL Server, Oracle. |

## Steps

1. **Normalise requirements.** Names are canonicalised through the alias dictionary
   (`JS` → JavaScript). Duplicates are merged case-insensitively; if a skill is both
   required and preferred, *required* wins; the highest weight of the winning kind is kept.
   Empty names, unknown kinds and non-positive weights are rejected (`MatchingError`).
2. **Classify each requirement.**
   * **matched**: the same canonical skill is in the resume.
   * **related**: not in the resume, but a skill from the same curated group is.
     Shown with the group as the reason. **Adds nothing to the score.**
   * **missing**: neither.
3. **Score.**

   ```
   required_coverage  = 100 × Σ weight(matched required)  / Σ weight(required)
   preferred_coverage = 100 × Σ weight(matched preferred) / Σ weight(preferred)

   score = s × required_coverage + (1 − s) × preferred_coverage    (both kinds present)
         = required_coverage                                       (no preferred skills)
         = preferred_coverage                                      (no required skills)
   ```

   `s` = `MATCHING_REQUIRED_SHARE` (default 0.8, allowed 0.5–1.0). Results are
   clamped to 0–100 and rounded to one decimal. A job with no skills at all
   cannot be analysed (`no_requirements`).
4. **Feedback** (all derived from the classification above):
   * *Strengths*: matched skills with evidence of use (a project or experience entry),
     quoting that evidence.
   * *Areas for improvement*: missing required skills (highest weight first), and
     matched skills that are only listed, never shown in use.
   * *Suggestions*: per missing required skill. When a related skill exists, the
     suggestion is to add the skill *if the user has used it*, otherwise to present the
     related experience as transferable. The engine never suggests claiming a skill the
     user doesn't have. Unconfirmed parser-detected matches are flagged for review.

## Worked example

Resume: Python, PostgreSQL, React (Skills); Django, PostgreSQL, React (project "Inventory Tracker").

| Requirement | Kind | Weight | Result |
|---|---|---|---|
| Python | required | 2 | matched (Skills section) |
| Django | required | 1 | matched (Project: Inventory Tracker) |
| Docker | required | 1 | missing |
| MySQL | required | 1 | related → PostgreSQL (relational SQL databases) |
| AWS | preferred | 1 | missing |
| React | preferred | 1 | matched |

required = (2 + 1) / 5 = 60.0 · preferred = 1 / 2 = 50.0 · **score = 0.8 × 60 + 0.2 × 50 = 58.0**

This exact case is an API integration test (`tests/test_jobs_analyses_api.py`).

## Design decisions

* **Deterministic first.** A transparent baseline can be unit-tested and explained in
  an interview. Semantic matching (sentence-transformers) is a planned, *optional*
  later phase. It will only add context and evidence, never silently turn "missing" into
  "matched", and it will be evaluated on a documented dataset before being enabled.
* **Related ≠ matched.** Knowing MySQL is relevant to a PostgreSQL role, but it is
  not proof of PostgreSQL experience, so it is shown but not scored.
* **Stored snapshots.** Each analysis stores its score, per-skill results, the
  settings used and the algorithm version, so history stays accurate after edits and
  future algorithm versions can be compared side by side.

## Known limitations

* Only skills are scored. Years of experience, education level and seniority are not.
* Skill detection depends on the dictionary (115 skills); unknown skills can still be
  added manually and match by exact (case-insensitive) name.
* Requirement suggestions from a job description are heuristic (heading/phrase rules);
  the user is expected to review them.
