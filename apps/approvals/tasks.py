from celery import shared_task

from apps.approvals.reminders import send_reminders


@shared_task
def send_pending_reminders():
    return send_reminders()
