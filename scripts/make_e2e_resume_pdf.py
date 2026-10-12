"""
Write the synthetic resume used by the Playwright end-to-end test.

The person and every detail are invented. The skills are chosen so the E2E
test can assert exact scores: Python, Django, PostgreSQL and React are present;
Kubernetes and AWS are deliberately absent.

Usage (from the backend virtualenv, repository root):
    python scripts/make_e2e_resume_pdf.py frontend/e2e/.generated/e2e-resume.pdf
"""
import sys
from pathlib import Path

import pymupdf

LINES = [
    "Riley Synthetic",
    "riley.synthetic@example.com",
    "",
    "SKILLS",
    "Python, Django, PostgreSQL, React",
    "",
    "EDUCATION",
    "B.Sc. Computer Science, Example State University, 2025",
    "",
    "PROJECTS",
    "Library Catalogue - Django app with PostgreSQL search and a React front end.",
]


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e-resume.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((72, y), line, fontsize=11)
        y += 16
    doc.save(out)
    doc.close()
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
