"""
Generate synthetic PDFs in memory for tests. No real resumes are used anywhere.
"""
import pymupdf

SAMPLE_RESUME_TEXT = [
    "Alex Example",
    "alex.example@example.com | +1 555 0100",
    "SKILLS",
    "Python, Django REST Framework, PostgreSQL, React, TypeScript",
    "EDUCATION",
    "B.Tech in Computer Science, Example Institute of Technology, 2025",
    "PROJECTS",
    "Inventory Tracker - built a Django API with PostgreSQL and a React UI.",
]


def make_pdf(pages: list[list[str]] | None = None) -> bytes:
    """Create a text-based PDF. `pages` is a list of pages, each a list of lines."""
    pages = pages if pages is not None else [SAMPLE_RESUME_TEXT]
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        y = 72
        for line in lines:
            page.insert_text((72, y), line, fontsize=11)
            y += 16
    data = doc.tobytes()
    doc.close()
    return data


def make_blank_pdf(page_count: int = 1) -> bytes:
    """A valid PDF with no text layer — stands in for a scanned/image-only resume."""
    doc = pymupdf.open()
    for _ in range(page_count):
        page = doc.new_page()
        # Draw a filled rectangle so the page isn't empty, but contains no text.
        page.draw_rect(pymupdf.Rect(72, 72, 300, 200), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
    data = doc.tobytes()
    doc.close()
    return data


def make_encrypted_pdf(user_password: str = "secret") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), " ".join(SAMPLE_RESUME_TEXT), fontsize=11)
    data = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw=user_password,
        owner_pw=user_password + "-owner",
    )
    doc.close()
    return data


def make_corrupt_pdf() -> bytes:
    """Has a valid signature but the body is garbage."""
    return b"%PDF-1.7\n" + b"\x00\xffthis is not a real pdf body" * 20 + b"\n%%EOF\n"
