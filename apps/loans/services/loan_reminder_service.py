from datetime import date
from decimal import Decimal
from typing import Optional, Dict

from django.utils import timezone

from apps.loans.models import Loan


class LoanReminderService:

    def __init__(self, loan: Loan, today: date, pre_due_days: int = 3):
        self.loan = loan
        self.today = today
        self.pre_due_days = pre_due_days

    def get_info(self) -> Optional[Dict]:
        """
        Determines reminder category and computes accurate financial values.
        """

        if self.loan.status not in ["disbursed", "overdue"]:
            return None

        if not self.loan.disbursement_date:
            return None

        balances = self.loan.calculate_remaining_balances()
        total_outstanding = sum(balances.values())

        if total_outstanding <= Decimal("0.00"):
            return None

        schedule = self.loan.generate_payment_schedule()

        # PRE-DUE
        upcoming = [
            p for p in schedule
            if p["payment_due_date"] > self.today
            and 0 < (p["payment_due_date"] - self.today).days <= self.pre_due_days
        ]

        if upcoming:
            next_payment = min(upcoming, key=lambda x: x["payment_due_date"])
            return {
                "category": "pre_due",
                "days_until": (next_payment["payment_due_date"] - self.today).days,
                "next_due_date": next_payment["payment_due_date"],
                "amount_upcoming": next_payment["total_payment"],
                **balances,
                "total_outstanding": total_outstanding,
            }

        # DUE TODAY
        today_installments = [
            p for p in schedule
            if p["payment_due_date"] == self.today
        ]

        if today_installments:
            expected = sum(p["total_payment"] for p in today_installments)
            real_due = self.loan.calculate_total_amount_due_balance(
                self.today,
                expected
            )

            if real_due > 0:
                return {
                    "category": "due_today",
                    "amount_due_today": real_due,
                    **balances,
                    "total_outstanding": total_outstanding,
                }

        # OVERDUE
        missed = [
            p for p in schedule
            if p["payment_due_date"] < self.today
        ]

        if missed:
            earliest = min(p["payment_due_date"] for p in missed)
            expected_overdue = sum(p["total_payment"] for p in missed)

            real_overdue = self.loan.calculate_total_amount_due_balance(
                self.today,
                expected_overdue
            )

            if real_overdue > 0:
                return {
                    "category": "overdue",
                    "days_overdue": (self.today - earliest).days,
                    "amount_overdue": real_overdue,
                    **balances,
                    "total_outstanding": total_outstanding,
                }

        # Maturity overdue
        if self.loan.due_date and self.loan.due_date < self.today:
            return {
                "category": "overdue",
                "days_overdue": (self.today - self.loan.due_date).days,
                "amount_overdue": total_outstanding,
                **balances,
                "total_outstanding": total_outstanding,
            }

        return None