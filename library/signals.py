from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import BorrowRecord
from django.utils import timezone
from datetime import timedelta


@receiver(post_save, sender=BorrowRecord)
def update_borrow_status(sender, instance, **kwargs):
    # Auto-update status to Overdue if past due date
    if instance.status == 'Borrowed' and timezone.now() > instance.due_date:
        instance.status = 'Overdue'
        instance.save(update_fields=['status'])
