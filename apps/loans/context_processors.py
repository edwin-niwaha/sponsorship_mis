import logging
from datetime import date, datetime

import pytz
from django.utils import timezone

from .models import Loan

logger = logging.getLogger(__name__)


def loans_due_today_context(request):
    try:
        timezone.activate(pytz.timezone("Africa/Nairobi"))
    except pytz.exceptions.UnknownTimeZoneError:
        timezone.activate(pytz.UTC)

    today = timezone.now().date()
    loans = Loan.objects.filter(status__in=["disbursed", "overdue"])
    due_loans = []
    overdue_loans = []

    for loan in loans:
        try:
            balances = loan.calculate_remaining_balances()
            total_balance = (
                balances["principal_balance"]
                + balances["interest_balance"]
                + balances["penalty_balance"]
            )
            if total_balance <= 0:
                continue
            schedule = loan.generate_payment_schedule()
            total_amount_due = total_balance
            if loan.due_date and loan.due_date < today:
                total_amount_due = total_balance
            else:
                payments = [
                    p
                    for p in schedule
                    if isinstance(p["payment_due_date"], (date, datetime))
                    and (
                        p["payment_due_date"].date()
                        if isinstance(p["payment_due_date"], datetime)
                        else p["payment_due_date"]
                    )
                    <= today
                    and p["principal_payment"] + p["interest_payment"] > 0
                ]
                if payments:
                    total_amount_due = min(
                        sum(
                            p["principal_payment"] + p["interest_payment"]
                            for p in payments
                        ),
                        total_balance,
                    )
            total_amount_due_balance = loan.calculate_total_amount_due_balance(
                due_date=today, total_amount_due=total_amount_due
            )
            if total_amount_due_balance <= 0:
                continue
            if not loan.disbursement_date or loan.loan_period_months <= 0:
                continue

            due_payments = [
                p
                for p in schedule
                if isinstance(p["payment_due_date"], (date, datetime))
                and (
                    p["payment_due_date"].date()
                    if isinstance(p["payment_due_date"], datetime)
                    else p["payment_due_date"]
                )
                == today
                and p["principal_payment"] + p["interest_payment"] > 0
            ]
            if due_payments:
                total_amount_due = min(
                    sum(
                        p["principal_payment"] + p["interest_payment"]
                        for p in due_payments
                    ),
                    total_balance,
                )
                total_amount_due_balance = loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                )
                if total_amount_due_balance <= 0:
                    continue
                due_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_balance": total_balance,
                        "due_payment": due_payments[0],
                        "disbursement_date": loan.disbursement_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                        "maturity_due_date": loan.due_date,
                    }
                )

            if loan.due_date and loan.due_date < today:
                days_overdue = (today - loan.due_date).days
                total_amount_due = total_balance
                total_amount_due_balance = loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                )
                if total_amount_due_balance <= 0:
                    continue
                overdue_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_balance": total_balance,
                        "disbursement_date": loan.disbursement_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                        "days_overdue": days_overdue,
                        "maturity_due_date": loan.due_date,
                    }
                )
            else:
                overdue_payments = [
                    p
                    for p in schedule
                    if isinstance(p["payment_due_date"], (date, datetime))
                    and (
                        p["payment_due_date"].date()
                        if isinstance(p["payment_due_date"], datetime)
                        else p["payment_due_date"]
                    )
                    < today
                    and p["principal_payment"] + p["interest_payment"] > 0
                ]
                if overdue_payments:
                    earliest_due_date = min(
                        (
                            p["payment_due_date"].date()
                            if isinstance(p["payment_due_date"], datetime)
                            else p["payment_due_date"]
                        )
                        for p in overdue_payments
                    )
                    days_overdue = (today - earliest_due_date).days
                    if days_overdue > 0:
                        total_amount_due = min(
                            sum(
                                p["principal_payment"] + p["interest_payment"]
                                for p in overdue_payments
                            ),
                            total_balance,
                        )
                        total_amount_due_balance = (
                            loan.calculate_total_amount_due_balance(
                                due_date=today, total_amount_due=total_amount_due
                            )
                        )
                        if total_amount_due_balance <= 0:
                            continue
                        overdue_loans.append(
                            {
                                "loan": loan,
                                "principal_balance": balances["principal_balance"],
                                "interest_balance": balances["interest_balance"],
                                "penalty_balance": balances["penalty_balance"],
                                "total_balance": total_balance,
                                "disbursement_date": loan.disbursement_date,
                                "total_amount_due": total_amount_due,
                                "total_amount_due_balance": total_amount_due_balance,
                                "days_overdue": days_overdue,
                                "maturity_due_date": loan.due_date,
                            }
                        )
        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    due_loans_count = len(due_loans)
    due_loans_total_amount = sum(loan["total_amount_due"] for loan in due_loans)
    due_loans_total_balance = sum(loan["total_balance"] for loan in due_loans)
    due_loans_total_due_balance = sum(
        loan["total_amount_due_balance"] for loan in due_loans
    )
    due_loans_total_penalty_balance = sum(loan["penalty_balance"] for loan in due_loans)

    overdue_loans_count = len(overdue_loans)
    overdue_loans_total_amount = sum(loan["total_amount_due"] for loan in overdue_loans)
    overdue_loans_total_balance = sum(loan["total_balance"] for loan in overdue_loans)
    overdue_loans_total_due_balance = sum(
        loan["total_amount_due_balance"] for loan in overdue_loans
    )
    overdue_loans_total_penalty_balance = sum(
        loan["penalty_balance"] for loan in overdue_loans
    )

    return {
        "due_loans": due_loans,
        "due_loans_count": due_loans_count,
        "due_loans_total_amount": due_loans_total_amount,
        "due_loans_total_balance": due_loans_total_balance,
        "due_loans_total_due_balance": due_loans_total_due_balance,
        "due_loans_total_penalty_balance": due_loans_total_penalty_balance,
        "overdue_loans": overdue_loans,
        "overdue_loans_count": overdue_loans_count,
        "overdue_loans_total_amount": overdue_loans_total_amount,
        "overdue_loans_total_balance": overdue_loans_total_balance,
        "overdue_loans_total_due_balance": overdue_loans_total_due_balance,
        "overdue_loans_total_penalty_balance": overdue_loans_total_penalty_balance,
    }
