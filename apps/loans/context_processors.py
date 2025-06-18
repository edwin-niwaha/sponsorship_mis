import logging
from datetime import date, datetime

import pytz
from django.utils import timezone

from .models import Loan

logger = logging.getLogger(__name__)


def loans_due_today_context(request):
    # Set timezone to Africa/Nairobi, fallback to UTC if timezone is invalid
    try:
        timezone.activate(pytz.timezone("Africa/Nairobi"))
    except pytz.exceptions.UnknownTimeZoneError:
        timezone.activate(pytz.UTC)

    # Get current date
    today = timezone.now().date()

    # Fetch all disbursed loans
    disbursed_loans = Loan.objects.filter(status="disbursed")
    due_loans = []  # List to store loans due today
    overdue_loans = []  # List to store overdue loans

    # Process each disbursed loan
    for loan in disbursed_loans:
        try:
            # Calculate remaining balances for the loan
            balances = loan.calculate_remaining_balances()
            total_balance = balances["principal_balance"] + balances["interest_balance"]
            if total_balance <= 0:
                continue  # Skip loans with zero or negative total balance

            # Generate payment schedule once
            schedule = loan.generate_payment_schedule()

            # Calculate total_amount_due for due or overdue scenarios
            total_amount_due = total_balance  # Default to total_balance
            if loan.due_date and loan.due_date < today:
                # Overdue past maturity
                total_amount_due = total_balance
            else:
                # Check for overdue or due payments
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
                continue  # Skip loans with zero or negative total_amount_due_balance
            if not loan.disbursement_date or loan.loan_period_months <= 0:
                continue

            # Identify payments due today
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
                and payment["principal_payment"] + payment["interest_payment"] > 0
            ]
            if due_payments:
                # Calculate total monthly installment for due payments
                monthly_installment = sum(
                    p["principal_payment"] + p["interest_payment"] for p in due_payments
                )
                total_amount_due = min(monthly_installment, total_balance)
                total_amount_due_balance = loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                )
                if total_amount_due_balance <= 0:
                    continue  # Re-check to ensure exclusion
                due_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "total_balance": total_balance,
                        "due_payment": due_payments[0],
                        "disbursement_date": loan.disbursement_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                    }
                )

            # Handle overdue loans
            if loan.due_date and loan.due_date < today:
                days_overdue = (today - loan.due_date).days
                total_amount_due = total_balance
                total_amount_due_balance = loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                )
                if total_amount_due_balance <= 0:
                    continue  # Re-check to ensure exclusion
                overdue_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "total_balance": total_balance,
                        "disbursement_date": loan.disbursement_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                        "days_overdue": days_overdue,
                    }
                )
            else:
                # Identify overdue payments before today
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
                if overdue_payments:
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
                        total_amount_due = min(monthly_installment, total_balance)
                        total_amount_due_balance = loan.calculate_total_amount_due_balance(
                            due_date=today, total_amount_due=total_amount_due
                        )
                        if total_amount_due_balance <= 0:
                            continue  # Re-check to ensure exclusion
                        overdue_loans.append(
                            {
                                "loan": loan,
                                "principal_balance": balances["principal_balance"],
                                "interest_balance": balances["interest_balance"],
                                "total_balance": total_balance,
                                "disbursement_date": loan.disbursement_date,
                                "total_amount_due": total_amount_due,
                                "total_amount_due_balance": total_amount_due_balance,
                                "days_overdue": days_overdue,
                            }
                        )
        except Exception as e:
            # Log error if loan processing fails
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    # Calculate summary statistics for due loans
    due_loans_count = len(due_loans)
    due_loans_total_amount = sum(loan["total_amount_due"] for loan in due_loans)
    due_loans_total_balance = sum(loan["total_balance"] for loan in due_loans)
    due_loans_total_due_balance = sum(
        loan["total_amount_due_balance"] for loan in due_loans
    )

    # Calculate summary statistics for overdue loans
    overdue_loans_count = len(overdue_loans)
    overdue_loans_total_amount = sum(loan["total_amount_due"] for loan in overdue_loans)
    overdue_loans_total_balance = sum(loan["total_balance"] for loan in overdue_loans)
    overdue_loans_total_due_balance = sum(
        loan["total_amount_due_balance"] for loan in overdue_loans
    )

    # Return context dictionary with loan data
    return {
        "due_loans": due_loans,
        "due_loans_count": due_loans_count,
        "due_loans_total_amount": due_loans_total_amount,
        "due_loans_total_balance": due_loans_total_balance,
        "due_loans_total_due_balance": due_loans_total_due_balance,
        "overdue_loans": overdue_loans,
        "overdue_loans_count": overdue_loans_count,
        "overdue_loans_total_amount": overdue_loans_total_amount,
        "overdue_loans_total_balance": overdue_loans_total_balance,
        "overdue_loans_total_due_balance": overdue_loans_total_due_balance,
    }