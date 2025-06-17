import logging
from datetime import date, datetime

import pytz
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.loans.models import Loan

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sends professional HTML email notifications for loans due today and overdue, with summary to BOO and HOF"

    def get_html_template(self, content, title, is_summary=False):
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
                .btn-view i {{ margin-right: 0.5rem; }}
                .text-right {{ text-align: right; }}
                .footer {{ font-size: 0.85rem; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container {'my-5' if is_summary else 'my-4'}">
                <div class="card shadow-sm">
                    <div class="card-header text-white text-center">
                        <h3 class="mb-0">{title}</h3>
                    </div>
                    <div class="card-body">{content}</div>
                    <div class="card-footer text-center footer">
                        Pendeza Uganda Loan Management System
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
        email.send(fail_silently=False)
        logger.info(f"Email sent to {', '.join(recipients)}: {subject}")
        return 1, 0

    def process_loan(self, loan, today, url, due_summary, overdue_summary):
        balances = loan.calculate_remaining_balances()
        total_balance = balances["principal_balance"] + balances["interest_balance"]
        if (
            total_balance <= 0
            or not loan.disbursement_date
            or loan.loan_period_months <= 0
        ):
            return 0, 0

        schedule = loan.generate_payment_schedule()
        sent, failed = 0, 0

        # Due today
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
        ]
        if due_payments:
            amount_due = min(
                sum(
                    p["principal_payment"] + p["interest_payment"] for p in due_payments
                ),
                total_balance,
            )
            borrower = loan.borrower
            due_summary.append(
                {
                    "loan_id": loan.id,
                    "borrower_name": borrower.full_name,
                    "total_amount_due": amount_due,
                    "total_balance": total_balance,
                }
            )

            subject = f"Loan Payment Due Today - Loan ID: {loan.id}"
            text_content = (
                f"Dear {borrower.full_name},\n\n"
                f"Your payment for Loan ID: {loan.id} is due today, {today.strftime('%Y-%m-%d')}.\n"
                f"Amount Due: UGX {amount_due:,.2f}\nOutstanding Balance: UGX {total_balance:,.2f}\n"
                f"Details: {url}\n\nBest regards,\nPendeza Uganda"
            )
            html_content = self.get_html_template(
                f"""
                <p>Dear {borrower.full_name},</p>
                <p>Your payment for Loan ID: {loan.id} is due today, {today.strftime('%Y-%m-%d')}.</p>
                <table class="table table-striped">
                    <thead><tr><th>Loan ID</th><th class="text-right">Amount Due</th><th class="text-right">Outstanding Balance</th></tr></thead>
                    <tbody><tr><td>{loan.id}</td><td class="text-right">UGX {amount_due:,.2f}</td><td class="text-right">UGX {total_balance:,.2f}</td></tr></tbody>
                </table>
                <p>Please make your payment promptly to maintain your account in good standing.</p>
                """,
                subject,
            )
            s, f = self.send_email(
                subject, text_content, html_content, [borrower.email]
            )
            sent += s
            failed += f

        # Overdue
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
        days_overdue = (
            (today - loan.due_date).days
            if loan.due_date and loan.due_date < today
            else (
                (
                    today
                    - min(
                        (
                            p["payment_due_date"].date()
                            if isinstance(p["payment_due_date"], datetime)
                            else p["payment_due_date"]
                        )
                        for p in overdue_payments
                    )
                ).days
                if overdue_payments
                and min(
                    (
                        p["payment_due_date"].date()
                        if isinstance(p["payment_due_date"], datetime)
                        else p["payment_due_date"]
                    )
                    for p in overdue_payments
                )
                < today
                else 0
            )
        )

        if days_overdue > 0:
            amount_due = (
                total_balance
                if loan.due_date and loan.due_date < today
                else min(
                    sum(
                        p["principal_payment"] + p["interest_payment"]
                        for p in overdue_payments
                    ),
                    total_balance,
                )
            )
            borrower = loan.borrower
            overdue_summary.append(
                {
                    "loan_id": loan.id,
                    "borrower_name": borrower.full_name,
                    "total_amount_due": amount_due,
                    "total_balance": total_balance,
                    "days_overdue": days_overdue,
                }
            )

            subject = f"Overdue Loan Payment - Loan ID: {loan.id}"
            text_content = (
                f"Dear {borrower.full_name},\n\n"
                f"Your payment for Loan ID: {loan.id} is overdue as of {today.strftime('%Y-%m-%d')}.\n"
                f"Amount Due: UGX {amount_due:,.2f}\nOutstanding Balance: UGX {total_balance:,.2f}\n"
                f"Details: {url}\n\nBest regards,\nPendeza Uganda"
            )
            html_content = self.get_html_template(
                f"""
                <p>Dear {borrower.full_name},</p>
                <p>Your payment for Loan ID: {loan.id} is <span class="text-danger">overdue</span> as of {today.strftime('%Y-%m-%d')}.</p>
                <table class="table table-striped">
                    <thead><tr><th>Loan ID</th><th class="text-right">Amount Due</th><th class="text-right">Outstanding Balance</th></tr></thead>
                    <tbody><tr><td>{loan.id}</td><td class="text-right">UGX {amount_due:,.2f}</td><td class="text-right">UGX {total_balance:,.2f}</td></tr></tbody>
                </table>
                <p>Please settle the overdue amount immediately to avoid further action.</p>
                """,
                subject,
            )
            s, f = self.send_email(
                subject, text_content, html_content, [borrower.email]
            )
            sent += s
            failed += f

        return sent, failed

    def send_summary_email(self, due_summary, overdue_summary, today, url):
        recipients = [
            email for email in [settings.BOO_EMAIL, settings.HOF_EMAIL] if email
        ]
        if not recipients:
            logger.warning("No valid BOO_EMAIL or HOF_EMAIL provided")
            return 0, 0

        subject = f"Loan Status Summary - {today.strftime('%Y-%m-%d')}"
        due_rows = "".join(
            f"<tr><td><a href='{url}#{loan['loan_id']}'>{loan['loan_id']}</a></td><td>{loan['borrower_name']}</td>"
            f"<td class='text-right'>UGX {loan['total_amount_due']:,.2f}</td><td class='text-right'>UGX {loan['total_balance']:,.2f}</td></tr>"
            for loan in due_summary
        )
        overdue_rows = "".join(
            f"<tr><td><a href='{url}#{loan['loan_id']}'>{loan['loan_id']}</a></td><td>{loan['borrower_name']}</td>"
            f"<td class='text-right'>UGX {loan['total_amount_due']:,.2f}</td><td class='text-right'>UGX {loan['total_balance']:,.2f}</td></tr>"
            for loan in overdue_summary
        )

        due_count, due_amount, due_balance = (
            len(due_summary),
            sum(loan["total_amount_due"] for loan in due_summary),
            sum(loan["total_balance"] for loan in due_summary),
        )
        overdue_count, overdue_amount, overdue_balance = (
            len(overdue_summary),
            sum(loan["total_amount_due"] for loan in overdue_summary),
            sum(loan["total_balance"] for loan in overdue_summary),
        )

        text_content = (
            f"Dear Team,\n\nLoan Summary for {today.strftime('%Y-%m-%d')}:\n\n"
            f"Loans Due Today ({due_count}):\n"
            + (
                "\n".join(
                    f"Loan ID: {loan['loan_id']}, Borrower: {loan['borrower_name']}, "
                    f"Amount Due: UGX {loan['total_amount_due']:,.2f}, Balance: UGX {loan['total_balance']:,.2f}"
                    for loan in due_summary
                )
                + f"\nTotal Amount Due: UGX {due_amount:,.2f}\nTotal Balance: UGX {due_balance:,.2f}\n"
                if due_summary
                else "None\n"
            )
            + f"\nOverdue Loans ({overdue_count}):\n"
            + (
                "\n".join(
                    f"Loan ID: {loan['loan_id']}, Borrower: {loan['borrower_name']}, "
                    f"Amount Due: UGX {loan['total_amount_due']:,.2f}, "
                    f"Balance: UGX {loan['total_balance']:,.2f}"
                    for loan in overdue_summary
                )
                + f"\nTotal Amount Overdue: UGX {overdue_amount:,.2f}\nTotal Balance: UGX {overdue_balance:,.2f}\n"
                if overdue_summary
                else "None\n"
            )
            + f"\nDetails: {url}\n\nBest regards,\nPendeza Uganda"
        )
        html_content = self.get_html_template(
            f"""
            <p>Dear Team,</p>
            <h5>Loans Due Today ({due_count})</h5>
            {f'<table class="table table-striped"><thead><tr><th>Loan ID</th><th>Borrower</th><th class="text-right">Amount Due</th><th class="text-right">Outstanding Balance</th></tr></thead><tbody>{due_rows}</tbody></table>'
            f'<p>Total Amount Due: <strong>UGX {due_amount:,.2f}</strong></p><p>Total Outstanding Balance: <strong>UGX {due_balance:,.2f}</strong></p>' if due_summary else '<p class="text-muted">No loans due today.</p>'}
            <h5 class="mt-4">Overdue Loans ({overdue_count})</h5>
            {f'<table class="table table-striped"><thead><tr><th>Loan ID</th><th>Borrower</th><th class="text-right">Amount Due</th><th class="text-right">Outstanding Balance</th></tr></thead><tbody>{overdue_rows}</tbody></table>'
            f'<p>Total Amount Overdue: <strong>UGX {overdue_amount:,.2f}</strong></p><p>Total Outstanding Balance: <strong>UGX {overdue_balance:,.2f}</strong></p>' if overdue_summary else '<p class="text-muted">No overdue loans.</p>'}
            <p class="mt-4"><a href="{url}" class="btn btn-view btn-lg d-inline-flex align-items-center"><i class="bi bi-eye-fill"></i> View All Loans</a></p>
            """,
            subject,
            is_summary=True,
        )
        return self.send_email(subject, text_content, html_content, recipients)

    def handle(self, *args, **kwargs):
        try:
            timezone.activate(pytz.timezone("Africa/Nairobi"))
        except pytz.exceptions.UnknownTimeZoneError:
            timezone.activate(pytz.UTC)

        today = timezone.now().date()
        loans = Loan.objects.filter(status="disbursed")
        url = "https://sponsorwithpendeza.up.railway.app/loans/due-overdue-report/"
        due_summary, overdue_summary = [], []
        sent, failed = 0, 0

        for loan in loans:
            try:
                s, f = self.process_loan(loan, today, url, due_summary, overdue_summary)
                sent += s
                failed += f
            except Exception as e:
                logger.error(f"Error processing Loan {loan.id}: {e}")
                failed += 1

        if due_summary or overdue_summary:
            try:
                s, f = self.send_summary_email(due_summary, overdue_summary, today, url)
                sent += s
                failed += f
            except Exception as e:
                logger.error(f"Error sending summary email: {e}")
                failed += 1
        else:
            logger.info("No loans due or overdue today")

        self.stdout.write(self.style.SUCCESS(f"Emails sent: {sent}, Failed: {failed}"))
