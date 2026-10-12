# Architecture (Stages 1–5)

## Components

```
Browser / SPA (Stage 6)
   │  HTTPS, session cookie + X-CSRFToken
   ▼
Django + DRF  (/api/v1/)
   ├── core       health check, error envelope, pagination
   ├── accounts   User model, session auth endpoints
   ├── skills     Skill + SkillAlias dictionary (seeded by migration, edited in admin)
   ├── jobs       JobDescription + JobRequirement; jd_extractor suggests required/preferred skills
   ├── analyses   matching.py (pure engine) ◄── analysis_service.py (gathers evidence, stores results)
   └── resumes    ResumeViewSet ──► ResumeUploadSerializer
                                     └─► services/resume_ingestion.py
                                          ├─ pdf_validation.py  (name, type, size, signature)
                                          ├─ pdf_parser.py      (PyMuPDF → normalised text)
                                          ├─ persist Resume + file (private storage)
                                          └─ resume_parsing.py → parsing/ pipeline → structured rows
   │
   ├── PostgreSQL     users, sessions, resumes (+ extracted text)
   └── PRIVATE_MEDIA_ROOT   PDFs at resumes/<user_id>/<random>.pdf (never served)
```

## Upload request flow

1. `POST /api/v1/resumes/` (multipart). DRF authenticates the session, checks CSRF,
   applies the `uploads` throttle.
2. `ResumeUploadSerializer.validate_file` calls `inspect_resume_upload`, which runs
   validation and text extraction **before** anything is written. Any rejection
   becomes a field error with a stable code.
3. `create_resume` saves the file under a random name, then inserts the row in a
   transaction; if the insert fails, the file is deleted.
4. The response is the detail representation including extracted text.

## Key decisions

| Decision | Reason |
|---|---|
| Custom `User` model from day one, email login | Swapping the user model after the first migration is very costly in Django. |
| Session-cookie auth instead of JWT in localStorage | Keeps credentials out of JavaScript-readable storage; Django already provides CSRF, rotation and server-side logout. |
| Synchronous extraction in the request | Resumes are small (page/size limits); avoids a task queue in early stages. The `status` field leaves room for async processing later. |
| Reject bad files instead of storing failed records | Unusable files hold personal data with no benefit. |
| One `Resume` row per upload | Natural version history; structured data (Stage 4) will hang off each version. |
| Services layer under `apps/resumes/services/` | Parsing code is reusable, unit-testable without HTTP, and swappable (e.g. a non-AGPL PDF library). |
| UUID primary key for `Resume` | Non-guessable ids as defence in depth; ownership checks remain the real control. |
| Settings split base / development / production / test | Production hardening can't leak into dev, and tests run fast with predictable limits. |

## Data model (current)

`accounts.User` — `id`, `email` (unique), `full_name`, Django auth fields.

`resumes.Resume` — `id` (UUID), `owner` → User (CASCADE), `title`,
`original_filename`, `file`, `file_size` (>0), `sha256`, `page_count` (>0),
`status`, `error_code`, `extracted_text`, `created_at`, `updated_at`.
Indexes: `(owner, -created_at)` for listing, `(owner, sha256)` for duplicate detection later.

## Parsing pipeline (Stage 4)

All parsers are pure Python in `apps/resumes/services/parsing/` and are unit-tested
without a database.

| Step | Module | Approach |
|---|---|---|
| Sections | `section_extractor.py` | Heading lines matched against synonym lists ("Technical Skills", "Work Experience", "Academic Projects", ...). Known non-parsed headings ("Achievements", "Hobbies") close the previous section. Generic ALL-CAPS detection is deliberately avoided because project/company names are often capitalised. |
| Contact | `contact_extractor.py` | Email/phone/URL regexes; name = first 2-4 word alphabetic header line. Location is never guessed. |
| Skills | `skill_extractor.py` + `apps/skills/dictionary.py` | Dictionary matching with token boundaries, longest-alias-first, URL stripping. Ambiguous aliases (C, R, Go, Excel, DRF, Spring) only count inside the Skills section, case-sensitively. Each hit stores section + evidence line. |
| Education | `education_extractor.py` | Entries start at degree or institution keywords; grade, year ranges, field of study ("in X") extracted only when written. |
| Experience | `experience_extractor.py` | Entries anchored on date-range lines; header split into title / company / location. No dates → no entries + `experience_unstructured` warning (nothing invented). |
| Projects | `project_extractor.py` | Title lines vs description bullets; supports "Name - description" one-liners. Technologies = dictionary skills explicitly present in that project's text. |
| Certifications | `certification_extractor.py` | One per line; name / issuer / date split on separators. |
| Assemble | `resume_normalizer.py` | Runs the above, truncates to column limits, emits warnings. |

Confidence scores are intentionally not shown: the rules are deterministic, and
a made-up percentage would imply a calibration that doesn't exist. Instead every
entry carries `source` and `is_verified`, and skills carry evidence.

## Data model additions (Stage 4)

```
Resume 1──1 ResumeProfile            (user_edited flag protects edits)
Resume 1──* ResumeSkill ──* skills.Skill (nullable: custom skills allowed)
Resume 1──* ResumeEducation / ResumeExperience / ResumeProject / ResumeCertification
skills.Skill 1──* skills.SkillAlias  (case-insensitive unique alias, is_ambiguous)
```

Every list entry shares `source`, `is_verified`, `position`, timestamps (abstract
`ResumeEntry`). `ResumeSkill` has a unique constraint on `(resume, lower(name))`.
Relational tables (rather than one JSON blob) give per-entry validation,
editing and ownership checks, and let Stage 5 join resume skills to job
requirements in SQL.

## Data model additions (Stage 5)

```
User 1──* JobDescription 1──* JobRequirement ──* skills.Skill (nullable for custom skills)
User 1──* Analysis *──1 Resume
          Analysis *──1 JobDescription
          Analysis 1──* AnalysisSkillResult   (status matched | missing | related, evidence JSON, explanation)
skills.SkillGroup *──* skills.Skill            (curated related-skill families)
```

* `JobRequirement`: unique `(job, lower(name))`, `weight` 1–5 enforced by validators
  and a DB check constraint.
* `Analysis` stores score, coverages, settings used, algorithm version, feedback and
  title snapshots, a deliberate denormalisation so history doesn't change when the
  resume or job is edited later. Score has a 0–100 check constraint.
* Deleting a resume or job deletes its analyses (CASCADE); deleting a user deletes everything.
* The matching engine is pure Python; see [matching-algorithm.md](matching-algorithm.md).
