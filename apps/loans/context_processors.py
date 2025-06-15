from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pytz
from django.utils import timezone
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

from .models import Loan


def loans_due_today_context(request):
    # Set timezone to Africa/Nairobi
    try:
        timezone.activate(pytz.timezone("Africa/Nairobi"))
    except pytz.exceptions.UnknownTimeZoneError:
        timezone.activate(pytz.UTC)

    today = timezone.now().date()

    # Fetch all disbursed loans
    disbursed_loans = Loan.objects.filter(status="disbursed")
    due_loans = []
    overdue_loans = []

    # Process loans for due and overdue status
    for loan in disbursed_loans:
        try:
            # Calculate balances
            balances = loan.calculate_remaining_balances()
            total_balance = balances["principal_balance"] + balances["interest_balance"]
            if total_balance <= 0:
                continue

            # Skip invalid loans
            if not loan.disbursement_date or loan.loan_period_months <= 0:
                continue

            # Generate payment schedule
            schedule = loan.generate_payment_schedule()

            # Check for payments due today
            due_payments = [
                payment
                for payment in schedule
                if isinstance(payment["payment_due_date"], (date, datetime))
                and (
                    payment["payment_due_date"].date()
                    if isinstance(payment["payment_due_date"], datetime)
                    else payment["payment_due_date"]
                )
                == today
            ]

            if due_payments:
                monthly_installment = sum(
                    p["principal_payment"] + p["interest_payment"] for p in due_payments
                )
                # Adjust total_amount_due if monthly installment exceeds total_balance
                total_amount_due = min(monthly_installment, total_balance)
                due_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "total_balance": total_balance,
                        "due_payment": due_payments[0],
                        "disbursement_date": loan.disbursement_date,
                        "total_amount_due": total_amount_due,
                    }
                )

            # Check for overdue payments
            overdue_payments = [
                payment
                for payment in schedule
                if isinstance(payment["payment_due_date"], (date, datetime))
                and (
                    payment["payment_due_date"].date()
                    if isinstance(payment["payment_due_date"], datetime)
                    else payment["payment_due_date"]
                )
                < today
                and payment["principal_payment"] + payment["interest_payment"] > 0
            ]

            if loan.due_date and loan.due_date < today:
                days_overdue = (today - loan.due_date).days
                # Use total_balance as total_amount_due, capped at total_balance
                total_amount_due = total_balance
                overdue_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "total_balance": total_balance,
                        "disbursement_date": loan.disbursement_date,
                        "total_amount_due": total_amount_due,
                        "days_overdue": days_overdue,
                    }
                )
            elif overdue_payments:
                earliest_due_date = min(
                    (
                        payment["payment_due_date"].date()
                        if isinstance(payment["payment_due_date"], datetime)
                        else payment["payment_due_date"]
                    )
                    for payment in overdue_payments
                )
                if earliest_due_date < today:
                    days_overdue = (today - earliest_due_date).days
                    monthly_installment = sum(
                        p["principal_payment"] + p["interest_payment"]
                        for p in overdue_payments
                    )
                    # Adjust total_amount_due if monthly installment exceeds total_balance
                    total_amount_due = min(monthly_installment, total_balance)
                    overdue_loans.append(
                        {
                            "loan": loan,
                            "principal_balance": balances["principal_balance"],
                            "interest_balance": balances["interest_balance"],
                            "total_balance": total_balance,
                            "disbursement_date": loan.disbursement_date,
                            "total_amount_due": total_amount_due,
                            "days_overdue": days_overdue,
                        }
                    )
        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    # Calculate counts, total amounts due, and total outstanding balances
    due_loans_count = len(due_loans)
    due_loans_total_amount = sum(loan["total_amount_due"] for loan in due_loans)
    due_loans_total_balance = sum(loan["total_balance"] for loan in due_loans)
    overdue_loans_count = len(overdue_loans)
    overdue_loans_total_amount = sum(loan["total_amount_due"] for loan in overdue_loans)
    overdue_loans_total_balance = sum(loan["total_balance"] for loan in overdue_loans)

    return {
        "due_loans": due_loans,
        "due_loans_count": due_loans_count,
        "due_loans_total_amount": due_loans_total_amount,
        "due_loans_total_balance": due_loans_total_balance,
        "overdue_loans": overdue_loans,
        "overdue_loans_count": overdue_loans_count,
        "overdue_loans_total_amount": overdue_loans_total_amount,
        "overdue_loans_total_balance": overdue_loans_total_balance,
    }
