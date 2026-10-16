"""
Orchestrates the upload pipeline: validate -> extract text -> persist.

Known-bad input (wrong type, too big, corrupt, encrypted, scanned) is rejected
before anything is written, so unusable files are never stored.
"""
import hashlib
import logging
from dataclasses import dataclass
from pathlib import PurePath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from ..models import Resume
from .pdf_parser import PdfTextExtraction, extract_text_from_pdf
from .pdf_validation import validate_pdf_upload
from .resume_parsing import try_parse_and_store

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InspectedResume:
    filename: str
    data: bytes
    extraction: PdfTextExtraction


def inspect_resume_upload(uploaded_file: UploadedFile) -> InspectedResume:
    """Validate and extract. Raises ResumeUploadError on any rejection."""
    upload = validate_pdf_upload(uploaded_file)
    extraction = extract_text_from_pdf(
        upload.data,
        max_pages=settings.RESUME_MAX_PAGES,
        min_text_chars=settings.RESUME_MIN_TEXT_CHARS,
        max_text_chars=settings.RESUME_MAX_TEXT_CHARS,
    )
    return InspectedResume(filename=upload.filename, data=upload.data, extraction=extraction)


def create_resume(owner, inspected: InspectedResume, title: str | None = None) -> Resume:
    """Persist a validated resume. The stored file is removed if the DB write fails."""
    resume = Resume(
        owner=owner,
        title=(title or "").strip() or PurePath(inspected.filename).stem[:150] or "Resume",
        original_filename=inspected.filename,
        file_size=len(inspected.data),
        sha256=hashlib.sha256(inspected.data).hexdigest(),
        page_count=inspected.extraction.page_count,
        status=Resume.Status.TEXT_EXTRACTED,
        extracted_text=inspected.extraction.text,
    )
    if settings.RESUME_STORE_FILES:
        # The name passed here is ignored by resume_upload_path (server-generated name).
        resume.file.save("upload.pdf", ContentFile(inspected.data), save=False)
    try:
        with transaction.atomic():
            resume.save()
    except Exception:
        if resume.file:
            resume.file.storage.delete(resume.file.name)
        raise
    # Log identifiers and sizes only — never resume text or filenames.
    logger.info(
        "Resume stored id=%s owner=%s pages=%s bytes=%s",
        resume.id, owner.pk, resume.page_count, resume.file_size,
    )
    try_parse_and_store(resume)
    return resume
