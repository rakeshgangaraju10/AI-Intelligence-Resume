"""
Upload-level validation for resume PDFs, performed before any parsing.

Checks, in order:
  1. Filename is sanitised and must end in ".pdf".
  2. Browser-supplied Content-Type, if present, must be a PDF-compatible value
     (it is advisory only and never trusted on its own).
  3. Size is non-zero and within RESUME_MAX_UPLOAD_BYTES.
  4. File signature: the bytes must contain the "%PDF-" header within the first
     1024 bytes (as the PDF specification allows).

Whether the bytes are a *valid, readable* PDF is decided afterwards by the
PDF parser, which actually opens the document.
"""
import unicodedata
from dataclasses import dataclass

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from .errors import ResumeUploadError

PDF_SIGNATURE = b"%PDF-"
SIGNATURE_SEARCH_WINDOW = 1024
ALLOWED_CONTENT_TYPES = frozenset(
    {"application/pdf", "application/x-pdf", "application/octet-stream", ""}
)
MAX_FILENAME_LENGTH = 255
DEFAULT_FILENAME = "resume.pdf"


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str  # sanitised, display-only
    data: bytes


def sanitize_filename(raw_name: str | None) -> str:
    """
    Reduce a client-supplied filename to a safe display name.

    Strips any directory components (both / and \\), control characters and
    surrounding whitespace/dots. The result is only stored as metadata; files
    on disk always get a server-generated name.
    """
    if not raw_name:
        return DEFAULT_FILENAME
    name = unicodedata.normalize("NFC", str(raw_name))
    name = name.replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = name.strip().strip(".").strip()
    if not name:
        return DEFAULT_FILENAME
    if len(name) > MAX_FILENAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and len(ext) <= 10:
            name = stem[: MAX_FILENAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            name = name[:MAX_FILENAME_LENGTH]
    return name


def _read_bounded(uploaded_file: UploadedFile, limit: int) -> bytes:
    """Read at most `limit + 1` bytes so an oversized stream can't exhaust memory."""
    uploaded_file.seek(0)
    chunks: list[bytes] = []
    remaining = limit + 1
    for chunk in uploaded_file.chunks():
        chunks.append(chunk[:remaining])
        remaining -= len(chunks[-1])
        if remaining <= 0:
            break
    return b"".join(chunks)


def validate_pdf_upload(uploaded_file: UploadedFile) -> ValidatedUpload:
    max_bytes: int = settings.RESUME_MAX_UPLOAD_BYTES
    filename = sanitize_filename(getattr(uploaded_file, "name", None))

    if not filename.lower().endswith(".pdf"):
        raise ResumeUploadError("invalid_extension", "Only PDF files (.pdf) are accepted.")

    content_type = (getattr(uploaded_file, "content_type", "") or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ResumeUploadError(
            "invalid_content_type", "The uploaded file does not appear to be a PDF."
        )

    declared_size = getattr(uploaded_file, "size", None)
    if declared_size is not None and declared_size > max_bytes:
        raise ResumeUploadError("file_too_large", _too_large_message(max_bytes))

    data = _read_bounded(uploaded_file, max_bytes)
    if not data:
        raise ResumeUploadError("empty_file", "The uploaded file is empty.")
    if len(data) > max_bytes:
        raise ResumeUploadError("file_too_large", _too_large_message(max_bytes))

    if data.find(PDF_SIGNATURE, 0, SIGNATURE_SEARCH_WINDOW) == -1:
        raise ResumeUploadError(
            "invalid_signature",
            "The file content is not a PDF, even though its name ends in .pdf.",
        )

    return ValidatedUpload(filename=filename, data=data)


def _too_large_message(max_bytes: int) -> str:
    return f"The file is larger than the {max_bytes / (1024 * 1024):.1f} MB limit."
