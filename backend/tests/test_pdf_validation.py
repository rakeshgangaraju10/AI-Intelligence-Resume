import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.resumes.services.errors import ResumeUploadError
from apps.resumes.services.pdf_validation import sanitize_filename, validate_pdf_upload

from .pdf_factory import make_pdf


def upload(data: bytes, name: str = "resume.pdf", content_type: str = "application/pdf"):
    return SimpleUploadedFile(name, data, content_type=content_type)


def error_code(callable_, *args) -> str:
    with pytest.raises(ResumeUploadError) as info:
        callable_(*args)
    return info.value.code


class TestSanitizeFilename:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("resume.pdf", "resume.pdf"),
            ("../../etc/passwd.pdf", "passwd.pdf"),
            ("..\\..\\windows\\evil.pdf", "evil.pdf"),
            ("/abs/path/My CV.pdf", "My CV.pdf"),
            ("bad\x00name\x1f.pdf", "badname.pdf"),
            ("   ", "resume.pdf"),
            ("..", "resume.pdf"),
            ("", "resume.pdf"),
            (None, "resume.pdf"),
        ],
    )
    def test_strips_paths_and_control_chars(self, raw, expected):
        assert sanitize_filename(raw) == expected

    def test_truncates_long_names_but_keeps_extension(self):
        result = sanitize_filename("a" * 400 + ".pdf")
        assert len(result) == 255
        assert result.endswith(".pdf")


class TestValidatePdfUpload:
    def test_accepts_valid_pdf(self):
        data = make_pdf()
        result = validate_pdf_upload(upload(data, name="My Resume.PDF"))
        assert result.data == data
        assert result.filename == "My Resume.PDF"

    @pytest.mark.parametrize("name", ["resume.docx", "resume.pdf.exe", "resume", "resume.txt"])
    def test_rejects_non_pdf_extension(self, name):
        assert error_code(validate_pdf_upload, upload(make_pdf(), name=name)) == "invalid_extension"

    def test_rejects_non_pdf_content_type(self):
        f = upload(make_pdf(), content_type="image/png")
        assert error_code(validate_pdf_upload, f) == "invalid_content_type"

    @pytest.mark.parametrize("content_type", ["application/octet-stream", ""])
    def test_tolerates_generic_content_types(self, content_type):
        # Some browsers/OSes send these for PDFs; the signature check decides.
        validate_pdf_upload(upload(make_pdf(), content_type=content_type))

    def test_rejects_empty_file(self):
        assert error_code(validate_pdf_upload, upload(b"")) == "empty_file"

    def test_rejects_file_over_size_limit(self, settings):
        settings.RESUME_MAX_UPLOAD_BYTES = 1000
        data = b"%PDF-1.7\n" + b"0" * 2000
        assert error_code(validate_pdf_upload, upload(data)) == "file_too_large"

    def test_rejects_disguised_file_with_pdf_name(self):
        """A PNG renamed to .pdf with a PDF content type must still be rejected."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert error_code(validate_pdf_upload, upload(png_bytes)) == "invalid_signature"

    def test_accepts_signature_after_small_preamble(self):
        # The PDF spec allows the header anywhere in the first 1024 bytes.
        data = b"junk-preamble\n" + make_pdf()
        validate_pdf_upload(upload(data))
