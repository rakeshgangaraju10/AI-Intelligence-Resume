import logging

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Resume

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Resume)
def delete_resume_file(sender, instance: Resume, **kwargs) -> None:
    """
    Remove the stored PDF once the row deletion is committed. Using a signal
    covers every path: API delete, admin delete and cascades from user deletion.
    """
    if not instance.file:
        return
    storage = instance.file.storage
    name = instance.file.name

    def _delete() -> None:
        try:
            storage.delete(name)
        except OSError:
            logger.warning("Could not delete stored file for resume id=%s", instance.pk)

    transaction.on_commit(_delete)
