import pytest

from apps.resumes.services.errors import ResumeUploadError
from apps.resumes.services.pdf_parser import extract_text_from_pdf, normalize_text

from .pdf_factory import (
    SAMPLE_RESUME_TEXT,
    make_blank_pdf,
    make_corrupt_pdf,
    make_encrypted_pdf,
    make_pdf,
)

LIMITS = {"max_pages": 5, "min_text_chars": 50, "max_text_chars": 200_000}


def extract(data: bytes, **overrides):
    return extract_text_from_pdf(data, **{**LIMITS, **overrides})


def error_code(data: bytes, **overrides) -> str:
    with pytest.raises(ResumeUploadError) as info:
        extract(data, **overrides)
    return info.value.code


class TestExtractText:
    def test_extracts_all_lines_from_single_page(self):
        result = extract(make_pdf())
        assert result.page_count == 1
        for line in SAMPLE_RESUME_TEXT:
            assert line in result.text
        assert result.char_count == len(result.text)

    def test_extracts_pages_in_order(self):
        pages = [SAMPLE_RESUME_TEXT, ["Second page marker: certifications section"]]
        result = extract(make_pdf(pages))
        assert result.page_count == 2
        assert result.text.index("Alex Example") < result.text.index("Second page marker")

    def test_encrypted_pdf_is_rejected(self):
        assert error_code(make_encrypted_pdf()) == "pdf_encrypted"

    def test_corrupt_pdf_is_rejected(self):
        assert error_code(make_corrupt_pdf()) == "pdf_corrupt"

    def test_truncated_pdf_is_rejected_or_has_no_text(self):
        # MuPDF can repair some truncation; either outcome must be a clean rejection.
        truncated = make_pdf()[:200]
        assert error_code(truncated) in {"pdf_corrupt", "pdf_no_text"}

    def test_scanned_style_pdf_without_text_is_rejected(self):
        assert error_code(make_blank_pdf()) == "pdf_no_text"

    def test_too_many_pages_is_rejected(self):
        pages = [[f"Page {i} " + "text " * 20] for i in range(4)]
        assert error_code(make_pdf(pages), max_pages=3) == "pdf_too_many_pages"

    def test_text_over_limit_is_rejected(self):
        assert error_code(make_pdf(), max_text_chars=100) == "pdf_text_too_long"

    def test_error_messages_never_contain_resume_content(self):
        with pytest.raises(ResumeUploadError) as info:
            extract(make_pdf(), max_text_chars=100)
        assert "Alex" not in info.value.message


class TestNormalizeText:
    def test_expands_ligatures_and_normalizes_whitespace(self):
        raw = "Certi\ufb01ed  \r\nline two   \n\n\n\n\nline three\x00"
        assert normalize_text(raw) == "Certified\nline two\n\nline three"

    def test_empty_input(self):
        assert normalize_text("  \n\n ") == ""
