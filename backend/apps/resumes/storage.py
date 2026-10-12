"""
Private storage for uploaded resumes.

Files live under settings.PRIVATE_MEDIA_ROOT, which is never mapped to a URL.
`url()` is overridden to raise ValueError instead of
producing a public link, so a resume can only be read by server code after an
ownership check. The model field references `private_resume_storage` (a
callable), so migrations store the callable path, never a local directory.
"""
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateResumeStorage(FileSystemStorage):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("location", str(settings.PRIVATE_MEDIA_ROOT))
        kwargs.setdefault("base_url", None)
        kwargs.setdefault("file_permissions_mode", 0o600)
        kwargs.setdefault("directory_permissions_mode", 0o700)
        super().__init__(**kwargs)

    def url(self, name: str | None) -> str:
        # FileSystemStorage falls back to MEDIA_URL when base_url is None; refuse
        # outright so no code path can ever build a link to a private resume.
        raise ValueError("Private resumes are not accessible via a URL.")


def private_resume_storage() -> PrivateResumeStorage:
    """Callable used by the model field so settings are read at runtime."""
    return PrivateResumeStorage()


def resume_upload_path(instance, filename: str) -> str:
    """
    Server-generated path: resumes/<owner_id>/<random>.pdf

    The client filename is never used on disk, which rules out path traversal,
    collisions and unsafe characters. The (sanitised) original name is kept
    only as display metadata in Resume.original_filename.
    """
    return f"resumes/{instance.owner_id}/{uuid.uuid4().hex}.pdf"
