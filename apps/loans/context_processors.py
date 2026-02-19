import logging
from datetime import date, datetime

import pytz
from django.utils import timezone

from .models import Loan

logger = logging.getLogger(__name__)

from apps.dashboard.views import get_loan_dashboard_summary


def loan_dashboard_context(request):
    """
    Safe context processor:
    - No DB loops
    - Uses cached summary only
    """
    try:
        summary = get_loan_dashboard_summary()
    except Exception:
        summary = {
            "due_loans_count": 0,
            "overdue_loans_count": 0,
        }

    return {
        "due_loans_count": summary["due_loans_count"],
        "overdue_loans_count": summary["overdue_loans_count"],
    }
