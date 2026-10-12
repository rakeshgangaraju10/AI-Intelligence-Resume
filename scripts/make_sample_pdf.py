"""
Write a synthetic resume PDF for manual testing (no real personal data).

Usage (from the backend virtualenv):
    python scripts/make_sample_pdf.py sample_resume.pdf
"""
import sys

import pymupdf

LINES = [
    "Jordan Sample",
    "jordan.sample@example.com",
    "",
    "SKILLS",
    "Python, Django, Django REST Framework, PostgreSQL, React, TypeScript, Docker, Git",
    "",
    "EDUCATION",
    "B.E. Computer Science (AI & ML), Example University, 2025",
    "",
    "PROJECTS",
    "Task Board API - REST API with Django REST Framework and PostgreSQL.",
    "Weather Dashboard - React + TypeScript frontend consuming a public weather API.",
    "",
    "CERTIFICATIONS",
    "Example Cloud Fundamentals (synthetic certificate for testing)",
]


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "sample_resume.pdf"
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
