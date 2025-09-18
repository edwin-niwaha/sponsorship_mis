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
        """
        Generates an HTML email template with Bootstrap styling.

        Args:
            content (str): The main HTML content for the email body.
            title (str): The title displayed in the email header.
            is_summary (bool): Indicates if the email is a summary report (affects styling).

        Returns:
            str: A complete HTML email template with the provided content and title.
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
                .table tfoot {{ font-weight: bold; background-color: #f8f9fa; }}
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
                        Pendeza Uganda - Loan Management System(LMS)
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def send_email(self, subject, text_content, html_content, recipients):
        """
        Sends an email with both plain text and HTML content.

        Args:
            subject (str): The subject line of the email.
            text_content (str): The plain text content of the email.
            html_content (str): The HTML content of the email.
            recipients (list): List of recipient email addresses.

        Returns:
            tuple: (sent, failed) where sent is the number of successful emails (1 or 0),
                   and failed is the number of failed emails (1 or 0).
        """
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

    def process_loan(self, loan, today, url, due_summary, overdue_summary):
        """
        Processes a single loan to determine if it is due or overdue, calculates balances,
        and sends email notifications to the borrower if applicable.

        Args:
            loan (Loan): The loan object to process.
            today (date): The current date for comparison.
            url (str): URL for loan details.
            due_summary (list): List to store details of loans due today.
            overdue_summary (list): List to store details of overdue loans.

        Returns:
            tuple: (sent, failed) where sent is the number of successful emails sent,
                   and failed is the number of failed emails.
        """
        # Calculate remaining balances for the loan
        try:
            balances = loan.calculate_remaining_balances()
            total_balance = (
                balances["principal_balance"]
                + balances["interest_balance"]
                + balances["penalty_balance"]
            )
            # Generate payment schedule to determine due or overdue payments
            schedule = loan.generate_payment_schedule()
            # Default total_amount_due to total_balance for simplicity
            total_amount_due = total_balance
            if loan.due_date and loan.due_date < today:
                # Loan is past maturity date, consider entire balance as overdue
                total_amount_due = total_balance
            else:
                # Identify overdue or due payments up to today
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
            # Calculate the total amount due balance, capped at total_balance to prevent exceeding
            total_amount_due_balance = min(
                loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                ),
                total_balance,
            )
            # Log values for debugging
            logger.info(
                f"Loan {loan.id}: total_balance={total_balance:,.2f}, "
                f"total_amount_due={total_amount_due:,.2f}, "
                f"total_amount_due_balance={total_amount_due_balance:,.2f}, "
                f"principal_balance={balances['principal_balance']:,.2f}, "
                f"interest_balance={balances['interest_balance']:,.2f}, "
                f"penalty_balance={balances['penalty_balance']:,.2f}"
            )
            # Skip loans with zero or negative balances
            if total_balance <= 0 or total_amount_due_balance <= 0:
                return 0, 0
            # Skip loans that are not disbursed or have invalid loan periods
            if not loan.disbursement_date or loan.loan_period_months <= 0:
                return 0, 0
        except Exception as e:
            logger.error(
                f"Error calculating balances or schedule for Loan {loan.id}: {e}"
            )
            return 0, 1

        sent, failed = 0, 0
        borrower = loan.borrower

        # Check for payments due today
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
            # Calculate total amount due for payments due today
            total_amount_due = min(
                sum(
                    p["principal_payment"] + p["interest_payment"] for p in due_payments
                ),
                total_balance,
            )
            # Cap total_amount_due_balance
            total_amount_due_balance = min(
                loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                ),
                total_balance,
            )
            # Log values for debugging
            logger.info(
                f"Loan {loan.id} (Due Today): total_balance={total_balance:,.2f}, "
                f"total_amount_due={total_amount_due:,.2f}, "
                f"total_amount_due_balance={total_amount_due_balance:,.2f}"
            )
            # Add loan details to due summary for reporting
            due_summary.append(
                {
                    "loan_id": loan.id,
                    "borrower_name": borrower.full_name,
                    "principal_amount": loan.principal_amount,
                    "interest_rate": loan.interest_rate,
                    "loan_period_months": loan.loan_period_months,
                    "disbursement_date": loan.disbursement_date,
                    "principal_balance": balances["principal_balance"],
                    "interest_balance": balances["interest_balance"],
                    "penalty_balance": balances["penalty_balance"],
                    "total_amount_due": total_amount_due,
                    "total_amount_due_balance": total_amount_due_balance,
                    "total_balance": total_balance,
                    "maturity_due_date": loan.due_date,
                }
            )

            # Prepare and send email for loans due today
            subject = f"Loan Payment Due Today - Ln Id: {loan.id}"
            text_content = (
                f"Dear {borrower.full_name},\n\n"
                f"Your payment for Ln Id: {loan.id} is due today, {today.strftime('%d/%m/%Y')}.\n"
                f"Principal Amount: {loan.principal_amount:,.2f}\n"
                f"Interest Rate: {loan.interest_rate:,.2f}%\n"
                f"Loan Period: {loan.loan_period_months} months\n"
                f"Disbursed: {loan.disbursement_date.strftime('%d/%m/%Y')}\n"
                f"Principal Balance: {balances['principal_balance']:,.2f}\n"
                f"Interest Balance: {balances['interest_balance']:,.2f}\n"
                f"Penalty Balance: {balances['penalty_balance']:,.2f}\n"
                f"Amount Due: {total_amount_due:,.2f}\n"
                f"Due Balance: {total_amount_due_balance:,.2f}\n"
                f"Outstanding Balance: {total_balance:,.2f}\n"
                f"Maturity: {loan.due_date.strftime('%d/%m/%Y')}\n"
                f"Details: {url}\n\nBest regards,\nPendeza Uganda"
            )
            html_content = self.get_html_template(
                f"""
                <p>Dear {borrower.full_name},</p>
                <p>Your payment for Ln Id: {loan.id} is due today, {today.strftime('%d/%m/%Y')}.</p>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Ln Id</th>
                            <th class="text-right">Principal Amount</th>
                            <th class="text-right">Rate (%)</th>
                            <th class="text-center">Period Months</th>
                            <th>Disbursed</th>
                            <th>Maturity</th>
                            <th class="text-right">Principal Balance</th>
                            <th class="text-right">Interest Balance</th>
                            <th class="text-right">Penalty Balance</th>
                            <th class="text-right">Due Balance</th>
                            <th class="text-right">Outstanding Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{loan.id}</td>
                            <td class="text-right">{loan.principal_amount:,.2f}</td>
                            <td class="text-right">{loan.interest_rate:,.2f}</td>
                            <td class="text-right">{loan.loan_period_months}</td>
                            <td>{loan.disbursement_date.strftime('%d/%m/%Y')}</td>
                            <td>{loan.due_date.strftime('%d/%m/%Y')}</td>
                            <td class="text-right">{balances['principal_balance']:,.2f}</td>
                            <td class="text-right">{balances['interest_balance']:,.2f}</td>
                            <td class="text-right">{balances['penalty_balance']:,.2f}</td>
                            <td class="text-right">{total_amount_due_balance:,.2f}</td>
                            <td class="text-right">{total_balance:,.2f}</td>
                        </tr>
                    </tbody>
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

        # Check for overdue loans (past maturity date)
        if loan.due_date and loan.due_date < today:
            days_overdue = (today - loan.due_date).days
            total_amount_due = total_balance
            total_amount_due_balance = min(
                loan.calculate_total_amount_due_balance(
                    due_date=today, total_amount_due=total_amount_due
                ),
                total_balance,
            )
            # Log values for debugging
            logger.info(
                f"Loan {loan.id} (Overdue): total_balance={total_balance:,.2f}, "
                f"total_amount_due={total_amount_due:,.2f}, "
                f"total_amount_due_balance={total_amount_due_balance:,.2f}"
            )
            # Skip if total_amount_due_balance is zero or negative
            if total_amount_due_balance <= 0:
                return sent, failed
            # Add loan details to overdue summary for reporting
            overdue_summary.append(
                {
                    "loan_id": loan.id,
                    "borrower_name": borrower.full_name,
                    "principal_amount": loan.principal_amount,
                    "interest_rate": loan.interest_rate,
                    "loan_period_months": loan.loan_period_months,
                    "disbursement_date": loan.disbursement_date,
                    "principal_balance": balances["principal_balance"],
                    "interest_balance": balances["interest_balance"],
                    "penalty_balance": balances["penalty_balance"],
                    "total_amount_due": total_amount_due,
                    "total_amount_due_balance": total_amount_due_balance,
                    "total_balance": total_balance,
                    "days_overdue": days_overdue,
                    "maturity_due_date": loan.due_date,
                }
            )

            # Prepare and send email for overdue loans
            subject = f"Overdue Loan Payment - Ln Id: {loan.id}"
            text_content = (
                f"Dear {borrower.full_name},\n\n"
                f"Your payment for Ln Id: {loan.id} is overdue as of {today.strftime('%d/%m/%Y')}.\n"
                f"Principal Amount: {loan.principal_amount:,.2f}\n"
                f"Interest Rate: {loan.interest_rate:,.2f}%\n"
                f"Loan Period: {loan.loan_period_months} months\n"
                f"Disbursed: {loan.disbursement_date.strftime('%d/%m/%Y')}\n"
                f"Principal Balance: {balances['principal_balance']:,.2f}\n"
                f"Interest Balance: {balances['interest_balance']:,.2f}\n"
                f"Penalty Balance: {balances['penalty_balance']:,.2f}\n"
                f"Amount Due: {total_amount_due:,.2f}\n"
                f"Due Balance: {total_amount_due_balance:,.2f}\n"
                f"Outstanding Balance: {total_balance:,.2f}\n"
                f"Maturity: {loan.due_date.strftime('%d/%m/%Y')}\n"
                f"Days Overdue: {days_overdue}\n"
                f"Details: {url}\n\nBest regards,\nPendeza Uganda"
            )
            html_content = self.get_html_template(
                f"""
                <p>Dear {borrower.full_name},</p>
                <p>Your payment for Ln Id: {loan.id} is <span class="text-danger">overdue</span> as of {today.strftime('%d/%m/%Y')}.</p>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Ln Id</th>
                            <th class="text-right">Principal Amount</th>
                            <th class="text-right">Rate (%)</th>
                            <th class="text-center">Period Months</th>
                            <th>Disbursed</th>
                            <th>Maturity</th>
                            <th class="text-right">Principal Balance</th>
                            <th class="text-right">Interest Balance</th>
                            <th class="text-right">Penalty Balance</th>
                            <th class="text-right">Due Balance</th>
                            <th class="text-right">Outstanding Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{loan.id}</td>
                            <td class="text-right">{loan.principal_amount:,.2f}</td>
                            <td class="text-right">{loan.interest_rate:,.2f}</td>
                            <td class="text-right">{loan.loan_period_months}</td>
                            <td>{loan.disbursement_date.strftime('%d/%m/%Y')}</td>
                            <td>{loan.due_date.strftime('%d/%m/%Y')}</td>
                            <td class="text-right">{balances['principal_balance']:,.2f}</td>
                            <td class="text-right">{balances['interest_balance']:,.2f}</td>
                            <td class="text-right">{balances['penalty_balance']:,.2f}</td>
                            <td class="text-right">{total_amount_due_balance:,.2f}</td>
                            <td class="text-right">{total_balance:,.2f}</td>
                        </tr>
                    </tbody>
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
        else:
            # Check for overdue installments before maturity
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
                # Calculate days overdue based on earliest missed payment
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
                    total_amount_due_balance = min(
                        loan.calculate_total_amount_due_balance(
                            due_date=today, total_amount_due=total_amount_due
                        ),
                        total_balance,
                    )
                    # Log values for debugging
                    logger.info(
                        f"Loan {loan.id} (Overdue Installments): total_balance={total_balance:,.2f}, "
                        f"total_amount_due={total_amount_due:,.2f}, "
                        f"total_amount_due_balance={total_amount_due_balance:,.2f}"
                    )
                    # Skip if total_amount_due_balance is zero or negative
                    if total_amount_due_balance <= 0:
                        return sent, failed
                    # Add loan details to overdue summary for reporting
                    overdue_summary.append(
                        {
                            "loan_id": loan.id,
                            "borrower_name": borrower.full_name,
                            "principal_amount": loan.principal_amount,
                            "interest_rate": loan.interest_rate,
                            "loan_period_months": loan.loan_period_months,
                            "disbursement_date": loan.disbursement_date,
                            "principal_balance": balances["principal_balance"],
                            "interest_balance": balances["interest_balance"],
                            "penalty_balance": balances["penalty_balance"],
                            "total_amount_due": total_amount_due,
                            "total_amount_due_balance": total_amount_due_balance,
                            "total_balance": total_balance,
                            "days_overdue": days_overdue,
                            "maturity_due_date": loan.due_date,
                        }
                    )

                    # Prepare and send email for overdue installments
                    subject = f"Overdue Loan Payment - Ln Id: {loan.id}"
                    text_content = (
                        f"Dear {borrower.full_name},\n\n"
                        f"Your payment for Ln Id: {loan.id} is overdue as of {today.strftime('%d/%m/%Y')}.\n"
                        f"Principal Amount: {loan.principal_amount:,.2f}\n"
                        f"Interest Rate: {loan.interest_rate:,.2f}%\n"
                        f"Loan Period: {loan.loan_period_months} months\n"
                        f"Disbursed: {loan.disbursement_date.strftime('%d/%m/%Y')}\n"
                        f"Principal Balance: {balances['principal_balance']:,.2f}\n"
                        f"Interest Balance: {balances['interest_balance']:,.2f}\n"
                        f"Penalty Balance: {balances['penalty_balance']:,.2f}\n"
                        f"Amount Due: {total_amount_due:,.2f}\n"
                        f"Due Balance: {total_amount_due_balance:,.2f}\n"
                        f"Outstanding Balance: {total_balance:,.2f}\n"
                        f"Maturity: {loan.due_date.strftime('%d/%m/%Y')}\n"
                        f"Days Overdue: {days_overdue}\n"
                        f"Details: {url}\n\nBest regards,\nPendeza Uganda"
                    )
                    html_content = self.get_html_template(
                        f"""
                        <p>Dear {borrower.full_name},</p>
                        <p>Your payment for Ln Id: {loan.id} is <span class="text-danger">overdue</span> as of {today.strftime('%d/%m/%Y')}.</p>
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Ln Id</th>
                                    <th class="text-right">Principal Amount</th>
                                    <th class="text-right">Rate (%)</th>
                                    <th class="text-center">Period Months</th>
                                    <th>Disbursed</th>
                                    <th>Maturity</th>
                                    <th class="text-right">Principal Balance</th>
                                    <th class="text-right">Interest Balance</th>
                                    <th class="text-right">Penalty Balance</th>
                                    <th class="text-right">Due Balance</th>
                                    <th class="text-right">Outstanding Balance</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{loan.id}</td>
                                    <td class="text-right">{loan.principal_amount:,.2f}</td>
                                    <td class="text-right">{loan.interest_rate:,.2f}</td>
                                    <td class="text-right">{loan.loan_period_months}</td>
                                    <td>{loan.disbursement_date.strftime('%d/%m/%Y')}</td>
                                    <td>{loan.due_date.strftime('%d/%m/%Y')}</td>
                                    <td class="text-right">{balances['principal_balance']:,.2f}</td>
                                    <td class="text-right">{balances['interest_balance']:,.2f}</td>
                                    <td class="text-right">{balances['penalty_balance']:,.2f}</td>
                                    <td class="text-right">{total_amount_due_balance:,.2f}</td>
                                    <td class="text-right">{total_balance:,.2f}</td>
                                </tr>
                            </tbody>
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
        """
        Sends a summary email to BOO and HOF with details of loans due today and overdue,
        sorted by loan_id, including total principal and interest balances, with a footer
        showing totals for relevant columns.

        Args:
            due_summary (list): List of dictionaries containing details of loans due today.
            overdue_summary (list): List of dictionaries containing details of overdue loans.
            today (date): The current date for the report.
            url (str): URL for accessing detailed loan reports.

        Returns:
            tuple: (sent, failed) where sent is the number of successful emails sent,
                   and failed is the number of failed emails.
        """
        # Gather recipient emails from settings
        recipients = [
            email for email in [settings.BOO_EMAIL, settings.HOF_EMAIL] if email
        ]
        if not recipients:
            logger.warning("No valid BOO_EMAIL or HOF_EMAIL provided")
            return 0, 0

        # Sort due_summary and overdue_summary by loan_id for consistent reporting
        due_summary = sorted(due_summary, key=lambda x: x["loan_id"])
        overdue_summary = sorted(overdue_summary, key=lambda x: x["loan_id"])

        subject = f"Loan Status Summary - {today.strftime('%d/%m/%Y')}"
        # Generate HTML table rows for due and overdue loans
        due_rows = "".join(
            f"<tr><td><a href='{url}#{loan['loan_id']}'>{loan['loan_id']}</a></td>"
            f"<td>{loan['borrower_name']}</td>"
            f"<td class='text-right'>{loan['principal_amount']:,.2f}</td>"
            f"<td class='text-right'>{loan['interest_rate']:,.2f}</td>"
            f"<td class='text-right'>{loan['loan_period_months']}</td>"
            f"<td>{loan['disbursement_date'].strftime('%d/%m/%Y')}</td>"
            f"<td>{loan['maturity_due_date'].strftime('%d/%m/%Y')}</td>"
            f"<td class='text-right'>{loan['principal_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['interest_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['penalty_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['total_amount_due_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['total_balance']:,.2f}</td></tr>"
            for loan in due_summary
        )
        # Calculate totals for footer (Loans Due Today)
        due_principal_total = sum(loan["principal_amount"] for loan in due_summary)
        due_principal_balance_total = sum(
            loan["principal_balance"] for loan in due_summary
        )
        due_interest_balance_total = sum(
            loan["interest_balance"] for loan in due_summary
        )
        due_penalty_balance_total = sum(loan["penalty_balance"] for loan in due_summary)
        due_amount_due_balance_total = sum(
            loan["total_amount_due_balance"] for loan in due_summary
        )
        due_balance_total = sum(loan["total_balance"] for loan in due_summary)
        # Footer row for due loans (only numeric columns)
        due_footer = (
            f"<tfoot><tr>"
            f"<td colspan='2'>Total</td>"
            f"<td class='text-right'>{due_principal_total:,.2f}</td>"
            f"<td></td>"  # Interest Rate: no meaningful total
            f"<td></td>"  # Loan Period: no meaningful total
            f"<td></td>"  # Disbursed: no total
            f"<td></td>"  # Maturity: no total
            f"<td class='text-right'>{due_principal_balance_total:,.2f}</td>"
            f"<td class='text-right'>{due_interest_balance_total:,.2f}</td>"
            f"<td class='text-right'>{due_penalty_balance_total:,.2f}</td>"
            f"<td class='text-right'>{due_amount_due_balance_total:,.2f}</td>"
            f"<td class='text-right'>{due_balance_total:,.2f}</td>"
            f"</tr></tfoot>"
            if due_summary
            else ""
        )

        overdue_rows = "".join(
            f"<tr><td><a href='{url}#{loan['loan_id']}'>{loan['loan_id']}</a></td>"
            f"<td>{loan['borrower_name']}</td>"
            f"<td class='text-right'>{loan['principal_amount']:,.2f}</td>"
            f"<td class='text-right'>{loan['interest_rate']:,.2f}</td>"
            f"<td class='text-right'>{loan['loan_period_months']}</td>"
            f"<td>{loan['disbursement_date'].strftime('%d/%m/%Y')}</td>"
            f"<td>{loan['maturity_due_date'].strftime('%d/%m/%Y')}</td>"
            f"<td class='text-right'>{loan['principal_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['interest_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['penalty_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['total_amount_due_balance']:,.2f}</td>"
            f"<td class='text-right'>{loan['total_balance']:,.2f}</td></tr>"
            for loan in overdue_summary
        )
        # Calculate totals for footer (Overdue Loans)
        overdue_principal_total = sum(
            loan["principal_amount"] for loan in overdue_summary
        )
        overdue_principal_balance_total = sum(
            loan["principal_balance"] for loan in overdue_summary
        )
        overdue_interest_balance_total = sum(
            loan["interest_balance"] for loan in overdue_summary
        )
        overdue_penalty_balance_total = sum(
            loan["penalty_balance"] for loan in overdue_summary
        )
        overdue_amount_due_balance_total = sum(
            loan["total_amount_due_balance"] for loan in overdue_summary
        )
        overdue_balance_total = sum(loan["total_balance"] for loan in overdue_summary)
        # Footer row for overdue loans (only numeric columns)
        overdue_footer = (
            f"<tfoot><tr>"
            f"<td colspan='2'>Total</td>"
            f"<td class='text-right'>{overdue_principal_total:,.2f}</td>"
            f"<td></td>"  # Interest Rate: no meaningful total
            f"<td></td>"  # Loan Period: no meaningful total
            f"<td></td>"  # Disbursed: no total
            f"<td></td>"  # Maturity: no total
            f"<td class='text-right'>{overdue_principal_balance_total:,.2f}</td>"
            f"<td class='text-right'>{overdue_interest_balance_total:,.2f}</td>"
            f"<td class='text-right'>{overdue_penalty_balance_total:,.2f}</td>"
            f"<td class='text-right'>{overdue_amount_due_balance_total:,.2f}</td>"
            f"<td class='text-right'>{overdue_balance_total:,.2f}</td>"
            f"</tr></tfoot>"
            if overdue_summary
            else ""
        )

        # Calculate summary statistics for loans due today
        due_count = len(due_summary)
        due_amount = sum(loan["total_amount_due"] for loan in due_summary)
        due_balance = sum(loan["total_balance"] for loan in due_summary)
        due_amount_due_balance = sum(
            loan["total_amount_due_balance"] for loan in due_summary
        )
        due_penalty_balance = sum(loan["penalty_balance"] for loan in due_summary)
        due_principal_balance = sum(loan["principal_balance"] for loan in due_summary)
        due_interest_balance = sum(loan["interest_balance"] for loan in due_summary)

        # Calculate summary statistics for overdue loans
        overdue_count = len(overdue_summary)
        overdue_amount = sum(loan["total_amount_due"] for loan in overdue_summary)
        overdue_balance = sum(loan["total_balance"] for loan in overdue_summary)
        overdue_amount_due_balance = sum(
            loan["total_amount_due_balance"] for loan in overdue_summary
        )
        overdue_penalty_balance = sum(
            loan["penalty_balance"] for loan in overdue_summary
        )
        overdue_principal_balance = sum(
            loan["principal_balance"] for loan in overdue_summary
        )
        overdue_interest_balance = sum(
            loan["interest_balance"] for loan in overdue_summary
        )

        # Prepare plain text content for the summary email
        text_content = (
            f"Dear Team,\n\nLoan Summary for {today.strftime('%d/%m/%Y')}:\n\n"
            f"Loans Due Today ({due_count}):\n"
            + (
                "\n".join(
                    f"Ln Id: {loan['loan_id']}, Borrower: {loan['borrower_name']}, "
                    f"Principal Amount: {loan['principal_amount']:,.2f}, "
                    f"Interest Rate: {loan['interest_rate']:,.2f}%, "
                    f"Loan Period: {loan['loan_period_months']} months, "
                    f"Disbursed: {loan['disbursement_date'].strftime('%d/%m/%Y')}, "
                    f"Principal Balance: {loan['principal_balance']:,.2f}, "
                    f"Interest Balance: {loan['interest_balance']:,.2f}, "
                    f"Penalty Balance: {loan['penalty_balance']:,.2f}, "
                    f"Amount Due: {loan['total_amount_due']:,.2f}, "
                    f"Due Balance: {loan['total_amount_due_balance']:,.2f}, "
                    f"Balance: {loan['total_balance']:,.2f}, "
                    f"Maturity: {loan['maturity_due_date'].strftime('%d/%m/%Y')}"
                    for loan in due_summary
                )
                + f"\nTotal Principal Balance: {due_principal_balance:,.2f}\n"
                + f"Total Interest Balance: {due_interest_balance:,.2f}\n"
                + f"Total Amount Due: {due_amount:,.2f}\n"
                + f"Total Due Balance: {due_amount_due_balance:,.2f}\n"
                + f"Total Penalty Balance: {due_penalty_balance:,.2f}\n"
                + f"Total Balance: {due_balance:,.2f}\n"
                if due_summary
                else "None\n"
            )
            + f"\nOverdue Loans ({overdue_count}):\n"
            + (
                "\n".join(
                    f"Ln Id: {loan['loan_id']}, Borrower: {loan['borrower_name']}, "
                    f"Principal Amount: {loan['principal_amount']:,.2f}, "
                    f"Interest Rate: {loan['interest_rate']:,.2f}%, "
                    f"Loan Period: {loan['loan_period_months']} months, "
                    f"Disbursed: {loan['disbursement_date'].strftime('%d/%m/%Y')}, "
                    f"Principal Balance: {loan['principal_balance']:,.2f}, "
                    f"Interest Balance: {loan['interest_balance']:,.2f}, "
                    f"Penalty Balance: {loan['penalty_balance']:,.2f}, "
                    f"Amount Due: {loan['total_amount_due']:,.2f}, "
                    f"Due Balance: {loan['total_amount_due_balance']:,.2f}, "
                    f"Balance: {loan['total_balance']:,.2f}, "
                    f"Maturity: {loan['maturity_due_date'].strftime('%d/%m/%Y')}, "
                    f"Days Overdue: {loan['days_overdue']}"
                    for loan in overdue_summary
                )
                + f"\nTotal Principal Balance: {overdue_principal_balance:,.2f}\n"
                + f"Total Interest Balance: {overdue_interest_balance:,.2f}\n"
                + f"Total Amount Overdue: {overdue_amount:,.2f}\n"
                + f"Total Due Balance: {overdue_amount_due_balance:,.2f}\n"
                + f"Total Penalty Balance: {overdue_penalty_balance:,.2f}\n"
                + f"Total Balance: {overdue_balance:,.2f}\n"
                if overdue_summary
                else "None\n"
            )
            + f"\nDetails: {url}\n\nBest regards,\nPendeza Uganda"
        )

        # Prepare HTML content for the summary email
        html_content = self.get_html_template(
            f"""
            <p>Dear Team,</p>
            <h5>Loans Due Today ({due_count})</h5>
            {f'<table class="table table-striped"><thead><tr><th>Ln Id</th><th>Borrower</th><th class="text-right">Principal Amount</th><th class="text-right">Rate (%)</th><th class="text-right">Period Months</th><th>Disbursed</th><th>Maturity</th><th class="text-right">Principal Balance</th><th class="text-right">Interest Balance</th><th class="text-right">Penalty Balance</th><th class="text-right">Due Balance</th><th class="text-right">Outstanding Balance</th></tr></thead><tbody>{due_rows}</tbody>{due_footer}</table>'
            f'<p>Total Principal Balance: <strong>{due_principal_balance:,.2f}</strong></p>'
            f'<p>Total Interest Balance: <strong>{due_interest_balance:,.2f}</strong></p>'
            f'<p>Total Amount Due: <strong>{due_amount:,.2f}</strong></p>'
            f'<p>Total Due Balance: <strong>{due_amount_due_balance:,.2f}</strong></p>'
            f'<p>Total Penalty Balance: <strong>{due_penalty_balance:,.2f}</strong></p>'
            f'<p>Total Outstanding Balance: <strong>{due_balance:,.2f}</strong></p>' if due_summary else '<p class="text-muted">No loans due today.</p>'}
            <h5 class="mt-4">Overdue Loans ({overdue_count})</h5>
            {f'<table class="table table-striped"><thead><tr><th>Ln Id</th><th>Borrower</th><th class="text-right">Principal Amount</th><th class="text-right">Rate (%)</th><th class="text-right">Period Months</th><th>Disbursed</th><th>Maturity</th><th class="text-right">Principal Balance</th><th class="text-right">Interest Balance</th><th class="text-right">Penalty Balance</th><th class="text-right">Due Balance</th><th class="text-right">Outstanding Balance</th></tr></thead><tbody>{overdue_rows}</tbody>{overdue_footer}</table>'
            f'<p>Total Principal Balance: <strong>{overdue_principal_balance:,.2f}</strong></p>'
            f'<p>Total Interest Balance: <strong>{overdue_interest_balance:,.2f}</strong></p>'
            f'<p>Total Amount Overdue: <strong>{overdue_amount:,.2f}</strong></p>'
            f'<p>Total Due Balance: <strong>{overdue_amount_due_balance:,.2f}</strong></p>'
            f'<p>Total Penalty Balance: <strong>{overdue_penalty_balance:,.2f}</strong></p>'
            f'<p>Total Outstanding Balance: <strong>{overdue_balance:,.2f}</strong></p>' if overdue_summary else '<p class="text-muted">No overdue loans.</p>'}
            <p class="mt-4"><a href="{url}" class="btn btn-view btn-lg d-inline-flex align-items-center"><i class="bi bi-eye-fill"></i> View All Loans</a></p>
            """,
            subject,
            is_summary=True,
        )
        return self.send_email(subject, text_content, html_content, recipients)

    def handle(self, *args, **kwargs):
        """
        Main entry point for the management command. Processes all disbursed or overdue loans
        and sends notifications and summary emails.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Outputs:
            Console message indicating the number of emails sent and failed.
        """
        # Set timezone to Africa/Nairobi or fallback to UTC
        try:
            timezone.activate(pytz.timezone("Africa/Nairobi"))
        except pytz.exceptions.UnknownTimeZoneError:
            timezone.activate(pytz.UTC)

        today = timezone.now().date()
        # Fetch all loans with status 'disbursed' or 'overdue'
        loans = Loan.objects.filter(status__in=["disbursed", "overdue"])
        url = "https://sponsorwithpendeza.org/loans/due-overdue-report/"
        due_summary, overdue_summary = [], []
        sent, failed = 0, 0

        # Process each loan for notifications
        for loan in loans:
            try:
                s, f = self.process_loan(loan, today, url, due_summary, overdue_summary)
                sent += s
                failed += f
            except Exception as e:
                logger.error(f"Error processing Loan {loan.id}: {e}")
                failed += 1

        # Send summary email if there are due or overdue loans
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
