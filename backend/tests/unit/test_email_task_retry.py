from sqlalchemy.exc import OperationalError

from app.tasks.charge_tasks import update_overdue_charges
from app.tasks.email_tasks import TransientEmailDeliveryError, send_daily_reminder_emails


def test_transient_email_delivery_error_is_retried():
    task = send_daily_reminder_emails._get_current_object()

    assert TransientEmailDeliveryError in task.autoretry_for


def test_overdue_charge_task_retries_only_database_operational_errors():
    task = update_overdue_charges._get_current_object()

    assert task.autoretry_for == (OperationalError,)
