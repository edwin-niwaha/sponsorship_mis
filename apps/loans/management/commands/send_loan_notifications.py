import logging
from datetime import date

import pytz
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.loans.models import Loan

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sends email notifications to borrowers for loans due today and overdue"

    def get_html_template(self, content, title):
        """
        Generates an HTML email template with Bootstrap styling.
        """
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f7fa; }}
                .card {{ border-radius: 10px; }}
                .card-header {{ background-color: #007bff; padding: 1rem; }}
                .table {{ background-color: #fff; border-radius: 8px; }}
                .table th {{ background-color: #e9ecef; }}
                .btn-view {{ 
                    background-color: #28a745; 
                    color: white; 
                    padding: 0.75rem 1.5rem; 
                    font-weight: 500; 
                    border-radius: 8px; 
                    transition: all 0.3s ease; 
                    border: none;
                }}
                .btn-view:hover {{ 
                    background-color: #218838; 
                    transform: translateY(-2px); 
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                }}
                .footer {{ font-size: 0.85rem; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container my-4">
                <div class="card shadow-sm">
                    <div class="card-header text-white text-center">
                        <h3 class="mb-0">{title}</h3>
                    </div>
                    <div class="card-body">{content}</div>
                    <div class="card-footer text-center footer">
                        Pendeza Uganda - Loan Management System
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def send_email(self, subject, text_content, html_content, recipients):
        email = EmailMultiAlternatives(
            subject, text_content, settings.DEFAULT_FROM_EMAIL, recipients
        )
        email.attach_alternative(html_content, "text/html")
        try:
            email.send(fail_silently=False)
            logger.info(f"Email sent to {', '.join(recipients)}: {subject}")
            return 1, 0
        except Exception as e:
            logger.error(f"Failed to send email to {', '.join(recipients)}: {e}")
            return 0, 1

    def process_loan(self, loan, today, url):
        """
        Check if loan has payments due today or is overdue → send reminder to borrower only
        """
        try:
            balances = loan.calculate_remaining_balances()
            total_balance = (
                balances["principal_balance"]
                + balances["interest_balance"]
                + balances["penalty_balance"]
            )

            if total_balance <= 0:
                return 0, 0

            if not loan.disbursement_date or loan.loan_period_months <= 0:
                return 0, 0

            schedule = loan.generate_payment_schedule()

        except Exception as e:
            logger.error(f"Error calculating balances/schedule for Loan {loan.id}: {e}")
            return 0, 1

        sent, failed = 0, 0
        borrower = loan.borrower
        borrower_email = borrower.email

        if not borrower_email:
            logger.warning(f"Loan {loan.id} - Borrower has no email address")
            return 0, 0

        # ───────────────────────────────────────────────
        # 1. Payments DUE TODAY
        # ───────────────────────────────────────────────
        due_payments = [
            p for p in schedule
            if getattr(p["payment_due_date"], 'date', lambda: p["payment_due_date"])() == today
            and p["principal_payment"] + p["interest_payment"] > 0
        ]

        if due_payments:
            amount_due_today = min(
                sum(p["principal_payment"] + p["interest_payment"] for p in due_payments),
                total_balance
            )
            due_balance = min(
                loan.calculate_total_amount_due_balance(due_date=today, total_amount_due=amount_due_today),
                total_balance
            )

            subject = f"Loan Payment Due Today - Ln Id: {loan.id}"

            text_content = (
                f"Dear {borrower.full_name},\n\n"
                f"Your payment for loan {loan.id} is due **today**, {today.strftime('%d/%m/%Y')}.\n\n"
                f"Principal Amount:       {loan.principal_amount:,.2f}\n"
                f"Amount Due Today:       {amount_due_today:,.2f}\n"
                f"Due Balance:            {due_balance:,.2f}\n"
                f"Outstanding Balance:    {total_balance:,.2f}\n"
                f"Maturity Date:          {loan.due_date.strftime('%d/%m/%Y') if loan.due_date else 'N/A'}\n"
                f"\nDetails: {url}\n\n"
                f"Please make your payment today.\n\n"
                f"Best regards,\nPendeza Uganda"
            )

            html_content = self.get_html_template(
                f"""
                <p>Dear <strong>{borrower.full_name}</strong>,</p>
                <p>Your loan payment (Ln Id: <strong>{loan.id}</strong>) is due <strong>today</strong>, {today.strftime('%d/%m/%Y')}.</p>
                <table class="table table-striped">
                    <tr><th>Item</th><th class="text-right">Amount</th></tr>
                    <tr><td>Principal Amount</td><td class="text-right">{loan.principal_amount:,.2f}</td></tr>
                    <tr><td>Amount Due Today</td><td class="text-right">{amount_due_today:,.2f}</td></tr>
                    <tr><td>Due Balance</td><td class="text-right">{due_balance:,.2f}</td></tr>
                    <tr><td>Outstanding Balance</td><td class="text-right">{total_balance:,.2f}</td></tr>
                    <tr><td>Maturity Date</td><td class="text-right">{loan.due_date.strftime('%d/%m/%Y') if loan.due_date else 'N/A'}</td></tr>
                </table>
                <p class="mt-3">Please make your payment promptly.</p>
                """,
                subject
            )

            s, f = self.send_email(subject, text_content, html_content, [borrower_email])
            sent += s
            failed += f

        # ───────────────────────────────────────────────
        # 2. OVERDUE (either past maturity or missed installments)
        # ───────────────────────────────────────────────
        is_overdue = False
        days_overdue = 0
        overdue_amount = total_balance

        if loan.due_date and loan.due_date < today:
            is_overdue = True
            days_overdue = (today - loan.due_date).days
        else:
            # Check missed installments before maturity
            overdue_payments = [
                p for p in schedule
                if getattr(p["payment_due_date"], 'date', lambda: p["payment_due_date"])() < today
                and p["principal_payment"] + p["interest_payment"] > 0
            ]
            if overdue_payments:
                is_overdue = True
                earliest = min(
                    getattr(p["payment_due_date"], 'date', lambda: p["payment_due_date"])()
                    for p in overdue_payments
                )
                days_overdue = (today - earliest).days

        if is_overdue and days_overdue > 0:
            due_balance = min(
                loan.calculate_total_amount_due_balance(due_date=today, total_amount_due=overdue_amount),
                total_balance
            )

            subject = f"Overdue Loan Payment - Ln Id: {loan.id}"

            text_content = (
                f"Dear {borrower.full_name},\n\n"
                f"Your loan {loan.id} is **OVERDUE** as of {today.strftime('%d/%m/%Y')}.\n\n"
                f"Principal Amount:       {loan.principal_amount:,.2f}\n"
                f"Amount Overdue:         {overdue_amount:,.2f}\n"
                f"Due Balance:            {due_balance:,.2f}\n"
                f"Outstanding Balance:    {total_balance:,.2f}\n"
                f"Maturity Date:          {loan.due_date.strftime('%d/%m/%Y') if loan.due_date else 'N/A'}\n"
                f"Days Overdue:           {days_overdue}\n"
                f"\nDetails: {url}\n\n"
                f"Please settle the overdue amount as soon as possible.\n\n"
                f"Best regards,\nPendeza Uganda"
            )

            html_content = self.get_html_template(
                f"""
                <p>Dear <strong>{borrower.full_name}</strong>,</p>
                <p class="text-danger fw-bold">Your loan payment (Ln Id: <strong>{loan.id}</strong>) is <u>OVERDUE</u> as of {today.strftime('%d/%m/%Y')}.</p>
                <table class="table table-striped">
                    <tr><th>Item</th><th class="text-right">Amount</th></tr>
                    <tr><td>Principal Amount</td><td class="text-right">{loan.principal_amount:,.2f}</td></tr>
                    <tr><td>Amount Overdue</td><td class="text-right">{overdue_amount:,.2f}</td></tr>
                    <tr><td>Due Balance</td><td class="text-right">{due_balance:,.2f}</td></tr>
                    <tr><td>Outstanding Balance</td><td class="text-right">{total_balance:,.2f}</td></tr>
                    <tr><td>Maturity Date</td><td class="text-right">{loan.due_date.strftime('%d/%m/%Y') if loan.due_date else 'N/A'}</td></tr>
                    <tr><td>Days Overdue</td><td class="text-right">{days_overdue}</td></tr>
                </table>
                <p class="mt-3 text-danger">Please settle immediately to avoid further action.</p>
                """,
                subject
            )

            s, f = self.send_email(subject, text_content, html_content, [borrower_email])
            sent += s
            failed += f

        return sent, failed

    def handle(self, *args, **kwargs):
        timezone.activate(pytz.timezone("Africa/Nairobi"))  # or fallback to UTC if needed

        today = timezone.now().date()
        loans = Loan.objects.filter(status__in=["disbursed", "overdue"])

        url = "https://sponsorwithpendeza.org/loans/due-overdue-report/"

        total_sent = 0
        total_failed = 0

        for loan in loans:
            try:
                sent, failed = self.process_loan(loan, today, url)
                total_sent += sent
                total_failed += failed
            except Exception as e:
                logger.error(f"Critical error processing loan {loan.id}: {e}")
                total_failed += 1

        if total_sent == 0 and total_failed == 0:
            self.stdout.write("No loans due or overdue today → no emails sent")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Emails sent: {total_sent}   |   Failed: {total_failed}"
            ))