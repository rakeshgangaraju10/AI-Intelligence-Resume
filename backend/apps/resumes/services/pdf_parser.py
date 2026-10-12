"""
PDF text extraction with PyMuPDF.

Operates purely on bytes (no filesystem paths), so it is easy to unit-test and
cannot be tricked into opening arbitrary files. OCR is NOT implemented: an
image-only (scanned) PDF is reported as `pdf_no_text` so the UI can explain it.
"""
import re
import unicodedata
from dataclasses import dataclass

import pymupdf

from .errors import ResumeUploadError

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TRAILING_SPACE = re.compile(r"[ \t]+\n")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class PdfTextExtraction:
    text: str
    page_count: int

    @property
    def char_count(self) -> int:
        return len(self.text)


def normalize_text(raw: str) -> str:
    """
    Make extracted text consistent for downstream parsing without changing meaning:
    NFKC (expands ligatures like 'ﬁ' -> 'fi', full-width chars), unified newlines,
    no control characters, no trailing spaces, at most one blank line in a row.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = _TRAILING_SPACE.sub("\n", text)
    text = _EXCESS_BLANK_LINES.sub("\n\n", text)
    return text.strip()


def extract_text_from_pdf(
    data: bytes,
    *,
    max_pages: int,
    min_text_chars: int,
    max_text_chars: int,
) -> PdfTextExtraction:
    """
    Extract plain text from PDF bytes.

    Raises ResumeUploadError with one of:
      pdf_corrupt, pdf_encrypted, pdf_too_many_pages, pdf_no_text, pdf_text_too_long
    """
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    # MuPDF can raise several exception types on malformed input (FileDataError,
    # low-level FzError* classes, ValueError). For untrusted uploads any failure
    # to open means "unreadable PDF", so the catch is intentionally broad.
    except Exception as exc:  # noqa: BLE001
        raise ResumeUploadError(
            "pdf_corrupt", "The PDF could not be opened. It may be damaged or incomplete."
        ) from exc

    with document:
        if document.needs_pass:
            raise ResumeUploadError(
                "pdf_encrypted",
                "The PDF is password-protected. Remove the password and upload it again.",
            )

        page_count = document.page_count
        if page_count == 0:
            raise ResumeUploadError("pdf_corrupt", "The PDF contains no pages.")
        if page_count > max_pages:
            raise ResumeUploadError(
                "pdf_too_many_pages",
                f"The PDF has {page_count} pages; the maximum allowed is {max_pages}.",
            )

        page_texts: list[str] = []
        total = 0
        try:
            for page in document:
                # sort=True orders blocks top-to-bottom, left-to-right, which reads
                # more naturally for multi-column resume layouts.
                page_text = page.get_text("text", sort=True)
                total += len(page_text)
                if total > max_text_chars * 2:  # cheap early exit before normalising
                    raise ResumeUploadError(
                        "pdf_text_too_long", "The PDF contains far more text than a resume."
                    )
                page_texts.append(page_text)
        except ResumeUploadError:
            raise
        except Exception as exc:  # noqa: BLE001 - same rationale as above
            raise ResumeUploadError(
                "pdf_corrupt", "The PDF could not be read. It may be damaged."
            ) from exc

    text = normalize_text("\n\n".join(page_texts))

    if len(text) > max_text_chars:
        raise ResumeUploadError(
            "pdf_text_too_long", "The PDF contains far more text than a resume."
        )
    if len(re.sub(r"\s", "", text)) < min_text_chars:
        raise ResumeUploadError(
            "pdf_no_text",
            "No selectable text was found. The PDF may be a scanned image; "
            "OCR is not supported yet, so please upload a text-based PDF "
            "(e.g. exported from Word or Google Docs).",
        )

    return PdfTextExtraction(text=text, page_count=page_count)
