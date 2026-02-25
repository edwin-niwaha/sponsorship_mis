import logging
from datetime import timedelta
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from apps.loans.models import Loan
from apps.loans.services.loan_reminder_service import LoanReminderService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Sends:
        • Pre-due reminders
        • Due today reminders
        • Overdue notices
        • Daily BOO summary report

    Safeguards:
        • 4-day cooldown per loan
        • Skips fully paid loans
        • Skips non-disbursed loans
        • Per-loan exception isolation
    """

    help = "Send automated loan reminders and BOO summary report."

    # --------------------------------------------------------
    # CLI ARGUMENTS
    # --------------------------------------------------------

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate sending emails without actually sending them.",
        )

        parser.add_argument(
            "--pre-due-days",
            type=int,
            default=7,
            help="Number of days before due date to send reminder.",
        )

    # --------------------------------------------------------
    # MAIN ENTRY POINT
    # --------------------------------------------------------

    def handle(self, *args, **options):

        self.dry_run = options["dry_run"]
        self.pre_due_days = options["pre_due_days"]

        today = timezone.localdate()

        if self.dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode"))

        logger.info("Loan reminder job started.")

        loans = (
            Loan.objects
            .filter(status__in=["disbursed", "overdue"])
            .select_related("borrower")
        )

        summary: Dict[str, List[Tuple[Loan, Dict]]] = {
            "pre_due": [],
            "due_today": [],
            "overdue": [],
        }

        total_processed = 0
        total_sent = 0

        for loan in loans.iterator():

            try:
                total_processed += 1

                # Cooldown protection (4 days)
                if loan.last_reminder_sent:
                    delta = timezone.now() - loan.last_reminder_sent
                    if delta < timedelta(days=4):
                        logger.debug(f"Loan #{loan.id} skipped (cooldown active)")
                        continue

                service = LoanReminderService(
                    loan=loan,
                    today=today,
                    pre_due_days=self.pre_due_days,
                )

                info = service.get_info()

                if not info:
                    continue

                sent = self.send_email(loan, info, today)

                if sent:
                    total_sent += 1
                    summary[info["category"]].append((loan, info))

                    # Update cooldown timestamp
                    loan.last_reminder_sent = timezone.now()
                    loan.save(update_fields=["last_reminder_sent"])

            except Exception:
                logger.exception(f"Loan #{loan.id} failed during processing.")

        # Send summary report
        self.send_summary(today, summary)

        logger.info("Loan reminder job completed.")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nProcessed: {total_processed} loans\n"
                f"Emails sent: {total_sent}\n"
                f"Pre-due: {len(summary['pre_due'])}\n"
                f"Due today: {len(summary['due_today'])}\n"
                f"Overdue: {len(summary['overdue'])}"
            )
        )

    # --------------------------------------------------------
    # SEND BORROWER EMAIL
    # --------------------------------------------------------

    def send_email(self, loan: Loan, info: Dict, today) -> bool:

        borrower = loan.borrower

        if not borrower.email:
            logger.warning(f"Loan #{loan.id} skipped (no borrower email)")
            return False

        category = info["category"]

        if category == "pre_due":
            subject = f"Upcoming Loan Payment – #{loan.id}"
            template = "emails/loan_pre_due.html"

        elif category == "due_today":
            subject = f"Loan Payment Due Today – #{loan.id}"
            template = "emails/loan_due_today.html"

        else:
            subject = f"Overdue Loan Payment – #{loan.id}"
            template = "emails/loan_overdue.html"

        context = {
            "loan": loan,
            "borrower": borrower,
            "today_str": today.strftime("%d %b %Y"),
            "detail_url": f"https://sponsorwithpendeza.org/loans/due-overdue-report/#{loan.id}",
            **info,
        }

        html_content = render_to_string(template, context)
        text_content = strip_tags(html_content)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would send {category} email to {borrower.email}")
            return True

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[borrower.email],
        )

        email.attach_alternative(html_content, "text/html")

        try:
            email.send(fail_silently=False)
            logger.info(f"{category} email sent to {borrower.email}")
            return True

        except Exception:
            logger.exception(f"Email failed for Loan #{loan.id}")
            return False

    # --------------------------------------------------------
    # SEND BOO SUMMARY
    # --------------------------------------------------------

    # def send_summary(self, today, summary):
    #     boo_email = getattr(settings, "BOO_EMAIL", None)

    #     if not boo_email:
    #         logger.warning("BOO_EMAIL not configured. Summary skipped.")
    #         return

    #     context = {
    #         "today_str": today.strftime("%d %b %Y"),
    #         "pre_due": [
    #             {"loan": l, "borrower_name": l.borrower.full_name, **i}
    #             for l, i in summary["pre_due"]
    #         ],
    #         "due_today": [
    #             {"loan": l, "borrower_name": l.borrower.full_name, **i}
    #             for l, i in summary["due_today"]
    #         ],
    #         "overdue": [
    #             {"loan": l, "borrower_name": l.borrower.full_name, **i}
    #             for l, i in summary["overdue"]
    #         ],
    #         "report_url": "https://sponsorwithpendeza.org/loans/due-overdue-report/",
    #     }

    #     subject = f"Loan Reminders Summary – {today.strftime('%d %b %Y')}"

    #     html = render_to_string("emails/loan_summary.html", context)
    #     text = strip_tags(html)

    #     if self.dry_run:
    #         logger.info(f"[DRY RUN] Would send summary to {boo_email}")
    #         return

    #     email = EmailMultiAlternatives(
    #         subject,
    #         text,
    #         settings.DEFAULT_FROM_EMAIL,
    #         [boo_email],
    #     )

    #     email.attach_alternative(html, "text/html")

    #     try:
    #         email.send(fail_silently=False)
    #         logger.info("Summary email sent successfully.")

    #     except Exception:
    #         logger.exception("Summary email failed.")

# Send email to both boo and finance team
    # --------------------------------------------------------
    # SEND BOO + HOF SUMMARY
    # --------------------------------------------------------

    def send_summary(self, today, summary):

        boo_email = getattr(settings, "BOO_EMAIL", None)
        hof_email = getattr(settings, "HOF_EMAIL", None)

        recipients = []

        if boo_email:
            recipients.append(boo_email)

        if hof_email:
            recipients.append(hof_email)

        if not recipients:
            logger.warning("No summary recipients configured. Summary skipped.")
            return

        context = {
            "today_str": today.strftime("%d %b %Y"),
            "pre_due": [
                {"loan": l, "borrower_name": l.borrower.full_name, **i}
                for l, i in summary["pre_due"]
            ],
            "due_today": [
                {"loan": l, "borrower_name": l.borrower.full_name, **i}
                for l, i in summary["due_today"]
            ],
            "overdue": [
                {"loan": l, "borrower_name": l.borrower.full_name, **i}
                for l, i in summary["overdue"]
            ],
            "report_url": "https://sponsorwithpendeza.org/loans/due-overdue-report/",
        }

        subject = f"Loan Reminders Summary – {today.strftime('%d %b %Y')}"

        html = render_to_string("emails/loan_summary.html", context)
        text = strip_tags(html)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would send summary to {recipients}")
            return

        email = EmailMultiAlternatives(
            subject,
            text,
            settings.DEFAULT_FROM_EMAIL,
            recipients,  # ✅ Now sends to both
        )

        email.attach_alternative(html, "text/html")

        try:
            email.send(fail_silently=False)
            logger.info(f"Summary email sent successfully to {recipients}.")

        except Exception:
            logger.exception("Summary email failed.")
