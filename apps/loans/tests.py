from datetime import date
from decimal import Decimal
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cloudinary import CloudinaryResource
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client as DjangoTestClient
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.client.models import Client
from apps.users.models import Profile

from .forms import LoanPenaltyForm, LoanRepaymentForm
from .models import (
    ChartOfAccounts,
    Loan,
    LoanApplicationDocument,
    LoanDisbursement,
    LoanPenalty,
    LoanRepayment,
    TransactionHistory,
)
from .services.reporting import (
    group_rows_by_bucket,
    loan_financial_row,
    portfolio_at_risk_summary,
)
from .services.loan_reminder_service import LoanReminderService
from .management.commands.send_loan_notifications import Command as LoanReminderCommand
from .tasks import (
    _loan_approval_payload,
    send_email_task,
    send_html_email_task,
    send_loan_application_email_task,
    send_loan_approval_notification_task,
    send_loan_stage_notification_task,
)
from .views import compute_installment_based_days_overdue


class LoanWorkflowTests(TestCase):
    def setUp(self):
        self.cash = ChartOfAccounts.objects.create(
            account_name="Cash", account_type="asset", account_number="1010"
        )
        self.loan_account = ChartOfAccounts.objects.create(
            account_name="Loan Receivable", account_type="asset", account_number="1050"
        )
        ChartOfAccounts.objects.create(
            account_name="Interest Receivable",
            account_type="asset",
            account_number="1060",
        )
        ChartOfAccounts.objects.create(
            account_name="Penalty Receivable",
            account_type="asset",
            account_number="1071",
        )
        ChartOfAccounts.objects.create(
            account_name="Interest Income",
            account_type="revenue",
            account_number="5030",
        )
        self.client = Client.objects.create(full_name="Jane Doe", reg_number="C001")
        self.boo = self._user("boo-user", "boo")
        self.hof = self._user("hof-user", "hof")
        self.ed = self._user("ed-user", "ed")
        self.accountant = self._user("accountant-user", "accountant")
        self.web = DjangoTestClient()

    def _user(self, username, role):
        user = User.objects.create_user(username=username, password="pass")
        Profile.objects.update_or_create(user=user, defaults={"role": role, "bio": ""})
        return user

    def _loan(self, **overrides):
        data = {
            "borrower": self.client,
            "principal_amount": Decimal("1000.00"),
            "interest_rate": Decimal("10.00"),
            "start_date": date(2026, 1, 1),
            "loan_period_months": 10,
            "status": "pending",
        }
        data.update(overrides)
        return Loan.objects.create(**data)

    def _attach_required_documents(self, loan, uploaded_by=None):
        for document_type in Loan.REQUIRED_DOCUMENT_TYPES:
            LoanApplicationDocument.objects.create(
                loan=loan,
                document_type=document_type,
                file=CloudinaryResource(
                    public_id=f"loan-documents/{loan.id}-{document_type}",
                    resource_type="auto",
                    type="upload",
                    format="pdf",
                ),
                uploaded_by=uploaded_by or self.boo,
            )

    def _approved_loan(self):
        loan = self._loan()
        self._attach_required_documents(loan)
        loan.approve(self.boo)
        loan.approve(self.hof)
        loan.approve(self.ed)
        loan.refresh_from_db()
        return loan

    def test_repayment_and_penalty_forms_include_only_active_loans_with_balance(self):
        disbursement_date = date(2026, 1, 2)
        disbursed = self._loan(
            status="disbursed", disbursement_date=disbursement_date
        )
        overdue = self._loan(status="overdue", disbursement_date=disbursement_date)
        repaid = self._loan(status="repaid")
        closed = self._loan(status="closed")
        rejected = self._loan(status="rejected")

        repayment_ids = set(
            LoanRepaymentForm().fields["loan"].queryset.values_list("id", flat=True)
        )
        penalty_ids = set(
            LoanPenaltyForm().fields["loan"].queryset.values_list("id", flat=True)
        )

        self.assertIn(disbursed.id, repayment_ids)
        self.assertIn(overdue.id, repayment_ids)
        self.assertNotIn(repaid.id, repayment_ids)
        self.assertNotIn(closed.id, repayment_ids)
        self.assertNotIn(rejected.id, repayment_ids)

        self.assertIn(disbursed.id, penalty_ids)
        self.assertIn(overdue.id, penalty_ids)
        self.assertNotIn(repaid.id, penalty_ids)
        self.assertNotIn(closed.id, penalty_ids)
        self.assertNotIn(rejected.id, penalty_ids)

    def test_forms_include_overdue_loans_with_paid_penalty_history(self):
        loan = self._loan(
            status="overdue",
            disbursement_date=date(2026, 1, 2),
            interest_rate=Decimal("0.00"),
        )
        LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 1, 3),
            principal_payment=Decimal("600.00"),
            interest_payment=Decimal("0.00"),
            penalty_payment=Decimal("0.00"),
            account=self.cash,
        )
        for penalty_date in (date(2026, 1, 4), date(2026, 1, 5)):
            LoanPenalty.objects.create(
                loan=loan,
                penalty_date=penalty_date,
                penalty_amount=Decimal("5.00"),
                remaining_amount=Decimal("5.00"),
                reason="Late payment",
                account=self.loan_account,
            )
        LoanPenalty.objects.filter(loan=loan).update(
            is_paid=True,
            remaining_amount=Decimal("0.00"),
        )
        loan.refresh_from_db()

        repayment_ids = set(
            LoanRepaymentForm().fields["loan"].queryset.values_list("id", flat=True)
        )
        penalty_ids = set(
            LoanPenaltyForm().fields["loan"].queryset.values_list("id", flat=True)
        )

        self.assertIn(loan.id, repayment_ids)
        self.assertIn(loan.id, penalty_ids)

    def test_loan_approval_chain_sets_audit_fields(self):
        loan = self._loan()
        self._attach_required_documents(loan)

        self.assertEqual(loan.approve(self.boo), "boo_approved")
        self.assertEqual(loan.approved_by_boo, self.boo)
        self.assertEqual(loan.approve(self.hof), "hof_approved")
        self.assertEqual(loan.approved_by_hof, self.hof)
        self.assertEqual(loan.approve(self.ed), "approved")
        self.assertEqual(loan.approved_by_ed, self.ed)
        self.assertEqual(loan.approved_date, timezone.localdate())

    def test_celery_memory_defaults_and_fire_and_forget_task_results(self):
        self.assertEqual(settings.CELERY_WORKER_CONCURRENCY, 1)
        self.assertEqual(settings.CELERY_WORKER_PREFETCH_MULTIPLIER, 1)
        self.assertEqual(settings.CELERY_WORKER_MAX_TASKS_PER_CHILD, 50)
        self.assertEqual(settings.CELERY_WORKER_MAX_MEMORY_PER_CHILD, 300000)
        self.assertEqual(settings.CELERY_TASK_SOFT_TIME_LIMIT, 300)
        self.assertEqual(settings.CELERY_TASK_TIME_LIMIT, 360)
        self.assertEqual(settings.CELERY_RESULT_EXPIRES, 3600)

        for task in [
            send_email_task,
            send_html_email_task,
            send_loan_stage_notification_task,
            send_loan_approval_notification_task,
            send_loan_application_email_task,
        ]:
            self.assertTrue(task.ignore_result)

    def test_loan_reminder_summary_item_does_not_retain_model_instance(self):
        loan = self._loan()
        info = {
            "category": "overdue",
            "notice_title": "Overdue loan payment",
            "action_label": "Overdue amount",
            "action_amount": Decimal("100.00"),
            "payment_due_date": date(2026, 1, 1),
            "total_outstanding": Decimal("100.00"),
            "days_overdue": 5,
        }

        item = LoanReminderCommand.summary_item(loan, info)

        self.assertEqual(item["loan"], {"id": loan.id})
        self.assertEqual(item["loan_id"], loan.id)
        self.assertEqual(item["borrower_name"], loan.borrower.full_name)
        self.assertNotIsInstance(item["loan"], Loan)

    @patch("apps.loans.tasks.EmailMultiAlternatives")
    def test_loan_application_email_skips_blocked_borrower_address(self, mock_email):
        sent = send_loan_application_email_task.run(
            recipient_name="Jane Doe",
            client_name="Jane Doe",
            recipient_email="pendezaug@gmail.com",
            application_id=123,
            is_applicant=True,
        )

        self.assertFalse(sent)
        mock_email.assert_not_called()

    @override_settings(BOO_EMAIL="", HOF_EMAIL="", ED_EMAIL="", ACCOUNTANT_EMAIL="")
    def test_stage_notifications_use_role_user_emails_when_settings_empty(self):
        self.boo.email = "boo@example.com"
        self.boo.save(update_fields=["email"])
        self.boo.profile.role = "staff"
        self.boo.profile.staff_role = "boo"
        self.boo.profile.save(update_fields=["role", "staff_role"])
        self.hof.email = "hof@example.com"
        self.hof.save(update_fields=["email"])
        self.hof.profile.role = "staff"
        self.hof.profile.staff_role = "hof"
        self.hof.profile.save(update_fields=["role", "staff_role"])
        self.ed.email = "ed@example.com"
        self.ed.save(update_fields=["email"])
        self.ed.profile.role = "staff"
        self.ed.profile.staff_role = "ed"
        self.ed.profile.save(update_fields=["role", "staff_role"])
        self.accountant.email = "accountant@example.com"
        self.accountant.save(update_fields=["email"])
        self.accountant.profile.role = "staff"
        self.accountant.profile.staff_role = "accountant"
        self.accountant.profile.save(update_fields=["role", "staff_role"])
        loan = self._loan()

        pending_payload = _loan_approval_payload(
            loan, "pending", "Loan Applicant", "https://example.test/"
        )
        boo_payload = _loan_approval_payload(
            loan, "boo_approved", "Business Officer", "https://example.test/"
        )
        hof_payload = _loan_approval_payload(
            loan, "hof_approved", "Head of Finance", "https://example.test/"
        )
        final_payload = _loan_approval_payload(
            loan, "approved", "Executive Director", "https://example.test/"
        )

        self.assertEqual(pending_payload["recipients"], ["boo@example.com"])
        self.assertEqual(boo_payload["recipients"], ["hof@example.com"])
        self.assertEqual(hof_payload["recipients"], ["ed@example.com"])
        self.assertEqual(final_payload["recipients"], ["accountant@example.com"])

    @override_settings(
        BOO_EMAIL="boo@example.com",
        HOF_EMAIL="hof@example.com",
        ED_EMAIL="ed@example.com",
        ACCOUNTANT_EMAIL="accountant@example.com",
    )
    def test_stage_notifications_deduplicate_configured_and_role_emails(self):
        self.boo.email = "BOO@example.com"
        self.boo.save(update_fields=["email"])
        self.hof.email = "hof@example.com"
        self.hof.save(update_fields=["email"])
        self.ed.email = "ed@example.com"
        self.ed.save(update_fields=["email"])
        self.accountant.email = "ACCOUNTANT@example.com"
        self.accountant.save(update_fields=["email"])
        loan = self._loan()

        pending_payload = _loan_approval_payload(
            loan, "pending", "Loan Applicant", "https://example.test/"
        )
        final_payload = _loan_approval_payload(
            loan, "approved", "Executive Director", "https://example.test/"
        )

        self.assertEqual(pending_payload["recipients"], ["boo@example.com"])
        self.assertEqual(final_payload["recipients"], ["accountant@example.com"])

    @patch("apps.loans.views.send_loan_approval_notification_task.delay")
    def test_approve_loan_returns_success_notification_and_queues_email(
        self, mock_delay
    ):
        loan = self._loan()
        self._attach_required_documents(loan)
        self.web.force_login(self.boo)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.web.get(reverse("loans:approve_loan", args=[loan.id]))
        loan.refresh_from_db()
        response_messages = [
            str(message) for message in get_messages(response.wsgi_request)
        ]

        self.assertRedirects(
            response,
            reverse("loans:loan_applications"),
            fetch_redirect_response=False,
        )
        self.assertEqual(loan.status, "boo_approved")
        self.assertTrue(
            any(
                "Approval notification queued." in message
                for message in response_messages
            )
        )
        mock_delay.assert_called_once()

    @patch("apps.loans.views.send_loan_approval_notification_task.delay")
    def test_approve_loan_blocks_when_required_documents_missing(self, mock_delay):
        loan = self._loan()
        self.web.force_login(self.boo)

        response = self.web.get(reverse("loans:approve_loan", args=[loan.id]))
        loan.refresh_from_db()
        response_messages = [
            str(message) for message in get_messages(response.wsgi_request)
        ]

        self.assertRedirects(
            response,
            reverse("loans:loan_detail", args=[loan.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(loan.status, "pending")
        self.assertTrue(
            any(
                "required supporting documents" in message
                for message in response_messages
            )
        )
        mock_delay.assert_not_called()

    def test_loan_detail_shows_attached_documents_before_review(self):
        loan = self._loan()
        self._attach_required_documents(loan, uploaded_by=self.boo)
        self.web.force_login(self.boo)

        response = self.web.get(reverse("loans:loan_detail", args=[loan.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attached Documents")
        self.assertContains(response, "National ID")
        self.assertContains(response, "Collateral / Security")
        self.assertContains(response, "View")
        self.assertContains(response, "Download")
        self.assertNotContains(
            response,
            "No supporting documents have been attached to this loan application.",
        )

    def test_loan_detail_shows_missing_required_documents_warning(self):
        loan = self._loan()
        self.web.force_login(self.boo)

        response = self.web.get(reverse("loans:loan_detail", args=[loan.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attached Documents")
        self.assertContains(
            response,
            "No supporting documents have been attached to this loan application.",
        )
        self.assertContains(response, "Required documents missing")
        self.assertContains(response, "Approval and review actions are blocked")

    def test_staff_document_open_is_scoped_to_selected_loan(self):
        loan = self._loan()
        self._attach_required_documents(loan, uploaded_by=self.boo)
        document = loan.documents.first()
        other_loan = self._loan(principal_amount=Decimal("2500.00"))
        self.web.force_login(self.boo)

        response = self.web.get(
            reverse(
                "loans:loan_application_document_open",
                args=[loan.id, document.id],
            )
        )
        blocked = self.web.get(
            reverse(
                "loans:loan_application_document_open",
                args=[other_loan.id, document.id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(document.file.public_id, response["Location"])
        self.assertEqual(blocked.status_code, 404)

    @patch("apps.loans.views.send_loan_stage_notification_task.delay")
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_staff_loan_application_adds_one_success_message(
        self, mock_applicant_delay, mock_stage_delay
    ):
        self.web.force_login(self.boo)

        response = self.web.post(
            reverse("loans:apply_for_loan"),
            {
                "client": self.client.id,
                "principal_amount": "1000.00",
                "interest_rate": "10.00",
                "loan_period_months": "6",
                "loan_purpose": "business",
                "start_date": "2026-01-01",
                "reason_for_approval": "Working capital",
            },
        )
        response_messages = [
            str(message) for message in get_messages(response.wsgi_request)
        ]

        self.assertRedirects(
            response,
            reverse("loans:loan_applications"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            response_messages.count("Loan application submitted successfully."),
            1,
        )
        mock_applicant_delay.assert_called_once()
        mock_stage_delay.assert_called_once()

    @patch("apps.loans.views.send_loan_approval_notification_task.delay")
    def test_approve_all_loans_queues_notifications_for_each_approved_loan(
        self, mock_delay
    ):
        first = self._loan()
        second = self._loan(principal_amount=Decimal("2000.00"))
        self._attach_required_documents(first)
        self._attach_required_documents(second)
        self.web.force_login(self.boo)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.web.get(reverse("loans:approve_all_loans"))
        response_messages = [
            str(message) for message in get_messages(response.wsgi_request)
        ]

        self.assertRedirects(
            response,
            reverse("loans:loan_applications"),
            fetch_redirect_response=False,
        )
        self.assertEqual(Loan.objects.filter(status="boo_approved").count(), 2)
        self.assertTrue(
            any(
                "Approval notifications queued." in message
                for message in response_messages
            )
        )
        self.assertEqual(mock_delay.call_count, 2)

    def test_disbursement_requires_approval(self):
        loan = self._loan()

        with self.assertRaises(ValidationError):
            loan.disburse(date(2026, 1, 2))

    def test_disbursement_sets_due_date_and_journal_once(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        disbursement = LoanDisbursement.objects.create(loan=loan, account=self.cash)

        self.assertEqual(loan.status, "disbursed")
        self.assertEqual(loan.due_date, date(2026, 11, 2))
        self.assertEqual(loan.transactions.count(), 4)

        disbursement.description = "Updated note"
        disbursement.save()
        self.assertEqual(loan.transactions.count(), 4)

    def test_disbursement_view_marks_loan_before_creating_disbursement(self):
        loan = self._approved_loan()
        self.web.force_login(self.hof)

        response = self.web.post(
            reverse("loans:disburse_loan"),
            {
                "loan": loan.id,
                "account": self.cash.id,
                "payment_method": "Cash",
                "disbursement_date": "2026-01-02",
            },
        )
        loan.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("loans:disburse_loan"),
            fetch_redirect_response=False,
        )
        self.assertEqual(loan.status, "disbursed")
        self.assertEqual(loan.disbursement_date, date(2026, 1, 2))
        self.assertEqual(loan.disbursements.count(), 1)
        self.assertEqual(loan.transactions.count(), 4)

    def test_disbursement_view_handles_approved_loan_without_receivable_account(self):
        loan = self._approved_loan()
        Loan.objects.filter(pk=loan.pk).update(account=None)
        self.web.force_login(self.hof)

        response = self.web.post(
            reverse("loans:disburse_loan"),
            {
                "loan": loan.id,
                "account": self.cash.id,
                "payment_method": "Cash",
                "disbursement_date": "2026-01-02",
            },
        )
        loan.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("loans:disburse_loan"),
            fetch_redirect_response=False,
        )
        self.assertEqual(loan.status, "disbursed")
        self.assertEqual(loan.account.account_number, "1050")
        self.assertEqual(loan.disbursements.count(), 1)
        self.assertEqual(loan.transactions.count(), 4)

    def test_duplicate_disbursement_is_rejected(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)

        with self.assertRaises(ValidationError):
            LoanDisbursement.objects.create(loan=loan, account=self.cash)

        self.assertEqual(loan.disbursements.count(), 1)
        self.assertEqual(loan.transactions.count(), 4)

    def test_repayment_cannot_exceed_outstanding_or_hit_closed_loan(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)

        with self.assertRaises(ValidationError):
            LoanRepayment.objects.create(
                loan=loan,
                repayment_date=date(2026, 2, 2),
                principal_payment=Decimal("2000.00"),
                account=self.cash,
            )

        loan.status = "closed"
        loan.save()
        with self.assertRaises(ValidationError):
            LoanRepayment.objects.create(
                loan=loan,
                repayment_date=date(2026, 2, 2),
                principal_payment=Decimal("10.00"),
                account=self.cash,
            )

    def test_repayment_cannot_be_before_disbursement(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 2, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)

        with self.assertRaises(ValidationError):
            LoanRepayment.objects.create(
                loan=loan,
                repayment_date=date(2026, 2, 1),
                principal_payment=Decimal("10.00"),
                account=self.cash,
            )

        self.assertEqual(loan.repayments.count(), 0)

    def test_penalty_balance_uses_remaining_unpaid_penalties(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        LoanPenalty.objects.create(
            loan=loan,
            penalty_date=date(2026, 2, 2),
            penalty_amount=Decimal("100.00"),
            reason="Late installment",
            account=ChartOfAccounts.objects.get(account_number="1071"),
        )

        LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 3),
            penalty_payment=Decimal("40.00"),
            account=self.cash,
        )

        self.assertEqual(
            loan.calculate_remaining_balances()["penalty_balance"], Decimal("60.00")
        )

    def test_penalty_remaining_amount_cannot_exceed_original_penalty(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)

        with self.assertRaises(ValidationError):
            LoanPenalty.objects.create(
                loan=loan,
                penalty_date=date(2026, 2, 2),
                penalty_amount=Decimal("100.00"),
                remaining_amount=Decimal("120.00"),
                reason="Late installment",
                account=ChartOfAccounts.objects.get(account_number="1071"),
            )

    def test_penalty_management_reverses_unpaid_penalty_instead_of_hard_delete(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        penalty = LoanPenalty.objects.create(
            loan=loan,
            penalty_date=date(2026, 2, 2),
            penalty_amount=Decimal("100.00"),
            reason="Late installment",
            account=ChartOfAccounts.objects.get(account_number="1071"),
        )
        web = DjangoTestClient()
        web.login(username="ed-user", password="pass")

        response = web.post(
            reverse("loans:loan_penalty_management"),
            {
                "client_id": self.client.id,
                "penalty_ids": [str(penalty.id)],
                "delete_selected": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        penalty.refresh_from_db()
        self.assertTrue(penalty.is_deleted)
        self.assertEqual(penalty.remaining_amount, Decimal("0.00"))
        self.assertEqual(
            TransactionHistory.objects.filter(
                loan=loan,
                description__icontains=f"penalty #{penalty.id}",
            ).count(),
            2,
        )

    def test_delete_repayment_removes_posted_journal_entries(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        repayment = LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 2),
            principal_payment=Decimal("100.00"),
            interest_payment=Decimal("10.00"),
            account=self.cash,
        )
        web = DjangoTestClient()
        web.login(username="ed-user", password="pass")

        response = web.post(
            reverse("loans:delete_repayment", args=[repayment.id]),
            HTTP_REFERER=reverse("loans:loan_detail", args=[loan.id]),
        )

        self.assertRedirects(
            response,
            reverse("loans:loan_detail", args=[loan.id]),
            fetch_redirect_response=False,
        )
        self.assertFalse(LoanRepayment.objects.filter(id=repayment.id).exists())
        self.assertFalse(
            TransactionHistory.objects.filter(
                loan=loan,
                transaction_date=repayment.repayment_date,
                description__icontains=f"Loan {loan.id}",
                amount__in=[Decimal("110.00"), Decimal("100.00"), Decimal("10.00")],
            ).exists()
        )

    def test_delete_repayment_removes_legacy_journal_entries_with_custom_descriptions(
        self,
    ):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        repayment = LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 2),
            principal_payment=Decimal("100.00"),
            interest_payment=Decimal("10.00"),
            account=self.cash,
        )
        TransactionHistory.objects.filter(
            loan=loan,
            transaction_date=repayment.repayment_date,
            amount__in=[Decimal("110.00"), Decimal("100.00"), Decimal("10.00")],
        ).update(description="Imported multijournal transaction")
        web = DjangoTestClient()
        web.login(username="ed-user", password="pass")

        response = web.post(
            reverse("loans:delete_repayment", args=[repayment.id]),
            HTTP_REFERER=reverse("loans:loan_detail", args=[loan.id]),
        )

        self.assertRedirects(
            response,
            reverse("loans:loan_detail", args=[loan.id]),
            fetch_redirect_response=False,
        )
        self.assertFalse(LoanRepayment.objects.filter(id=repayment.id).exists())
        self.assertFalse(
            TransactionHistory.objects.filter(
                loan=loan,
                transaction_date=repayment.repayment_date,
                description="Imported multijournal transaction",
            ).exists()
        )

    def test_delete_repayment_restores_penalty_balance(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 2))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        penalty = LoanPenalty.objects.create(
            loan=loan,
            penalty_date=date(2026, 2, 1),
            penalty_amount=Decimal("50.00"),
            reason="Late installment",
            account=ChartOfAccounts.objects.get(account_number="1071"),
        )
        repayment = LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 2),
            penalty_payment=Decimal("50.00"),
            account=self.cash,
        )
        penalty.refresh_from_db()
        self.assertTrue(penalty.is_paid)
        self.assertEqual(penalty.remaining_amount, Decimal("0.00"))
        web = DjangoTestClient()
        web.login(username="ed-user", password="pass")

        response = web.post(
            reverse("loans:delete_repayment", args=[repayment.id]),
            HTTP_REFERER=reverse("loans:loan_detail", args=[loan.id]),
        )

        self.assertRedirects(
            response,
            reverse("loans:loan_detail", args=[loan.id]),
            fetch_redirect_response=False,
        )
        penalty.refresh_from_db()
        self.assertFalse(LoanRepayment.objects.filter(id=repayment.id).exists())
        self.assertFalse(penalty.is_paid)
        self.assertEqual(penalty.remaining_amount, Decimal("50.00"))

    def test_standard_aging_bucket_inputs(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 1))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)

        aging = compute_installment_based_days_overdue(loan, date(2026, 3, 15))

        self.assertGreater(aging["days_overdue"], 0)
        self.assertGreater(aging["shortfall"], Decimal("0.00"))

    def test_loan_reminder_overdue_days_match_aging_report(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 1))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 1),
            principal_payment=loan.monthly_installment,
            account=self.cash,
        )
        today = date(2026, 3, 2)

        aging = compute_installment_based_days_overdue(loan, today)
        reminder_info = LoanReminderService(loan=loan, today=today).get_info()

        self.assertEqual(aging["days_overdue"], 1)
        self.assertEqual(reminder_info["category"], "overdue")
        self.assertEqual(reminder_info["days_overdue"], aging["days_overdue"])
        self.assertEqual(
            reminder_info["payment_due_date"],
            aging["first_unpaid_due_date"],
        )

    def test_loan_notification_command_sends_one_day_arrears_despite_cooldown(self):
        self.client.email = "borrower@example.com"
        self.client.save(update_fields=["email"])
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 1))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 1),
            principal_payment=loan.monthly_installment,
            account=self.cash,
        )
        loan.last_reminder_sent = timezone.now()
        loan.save(update_fields=["last_reminder_sent"])
        out = StringIO()

        with patch("django.utils.timezone.localdate", return_value=date(2026, 3, 2)):
            call_command("send_loan_notifications", "--dry-run", "--force", stdout=out)

        output = out.getvalue()
        self.assertIn("Emails sent: 1", output)
        self.assertIn("Overdue: 1", output)

    def test_loan_notification_command_skips_blocked_borrower_address(self):
        self.client.email = "pendezaug@gmail.com"
        self.client.save(update_fields=["email"])
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 1))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)
        LoanRepayment.objects.create(
            loan=loan,
            repayment_date=date(2026, 2, 1),
            principal_payment=loan.monthly_installment,
            account=self.cash,
        )
        out = StringIO()

        with patch("django.utils.timezone.localdate", return_value=date(2026, 3, 2)):
            call_command("send_loan_notifications", "--dry-run", "--force", stdout=out)

        output = out.getvalue()
        self.assertIn("Emails sent: 0", output)
        self.assertIn("Overdue: 0", output)

    def test_portfolio_at_risk_uses_outstanding_value_not_loan_count(self):
        at_risk = self._approved_loan()
        at_risk.disburse(date(2026, 1, 1))

        current = self._loan(
            borrower=Client.objects.create(
                full_name="Current Client", reg_number="C004"
            ),
            principal_amount=Decimal("2000.00"),
        )
        self._attach_required_documents(current)
        current.approve(self.boo)
        current.approve(self.hof)
        current.approve(self.ed)
        current.disburse(date(2026, 3, 1))

        rows = [
            loan_financial_row(at_risk, today=date(2026, 3, 15)),
            loan_financial_row(current, today=date(2026, 3, 15)),
        ]

        par = portfolio_at_risk_summary(rows)
        par_30 = next(band for band in par["bands"] if band["bucket"] == "PAR 30+")

        self.assertEqual(par["total_portfolio"], Decimal("3300.00"))
        self.assertEqual(par_30["outstanding_amount"], Decimal("1100.00"))
        self.assertEqual(par_30["loan_count"], 1)
        self.assertEqual(
            par_30["portfolio_percent"].quantize(Decimal("0.01")), Decimal("33.33")
        )

    def test_bucket_grouping_uses_standard_aging_order(self):
        rows = [
            {
                "aging_bucket": "61-90 days overdue",
                "outstanding_amount": Decimal("90.00"),
            },
            {"aging_bucket": "Current", "outstanding_amount": Decimal("10.00")},
            {
                "aging_bucket": "1-30 days overdue",
                "outstanding_amount": Decimal("30.00"),
            },
        ]

        grouped = group_rows_by_bucket(rows, "aging_bucket", ["outstanding_amount"])

        self.assertEqual(
            [bucket["key"] for bucket in grouped],
            ["Current", "1-30 days overdue", "61-90 days overdue"],
        )


class ClientSelfServiceLoanApplicationTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.web = DjangoTestClient()
        ChartOfAccounts.objects.create(
            account_name="Cash", account_type="asset", account_number="1010"
        )
        ChartOfAccounts.objects.create(
            account_name="Loan Receivable", account_type="asset", account_number="1050"
        )
        ChartOfAccounts.objects.create(
            account_name="Interest Receivable",
            account_type="asset",
            account_number="1060",
        )
        ChartOfAccounts.objects.create(
            account_name="Penalty Receivable",
            account_type="asset",
            account_number="1071",
        )
        ChartOfAccounts.objects.create(
            account_name="Interest Income",
            account_type="revenue",
            account_number="5030",
        )
        self.borrower = Client.objects.create(
            full_name="Mary Akello",
            reg_number="C002",
            email="mary@example.com",
        )
        self.other_client = Client.objects.create(
            full_name="John Okello",
            reg_number="C003",
            email="john@example.com",
        )
        self.user = self._user("mary", "mary@example.com", "guest")
        self.other_user = self._user("john", "john@example.com", "guest")
        self.boo = self._user("boo-user", "boo@example.com", "boo")
        self.hof = self._user("hof-user", "hof@example.com", "hof")
        self.ed = self._user("ed-user", "ed@example.com", "ed")

    def _user(self, username, email, role):
        user = User.objects.create_user(username=username, email=email, password="pass")
        Profile.objects.update_or_create(user=user, defaults={"role": role, "bio": ""})
        return user

    def _upload(self, name="document.pdf"):
        return SimpleUploadedFile(
            name, b"test file content", content_type="application/pdf"
        )

    def _post_data(self):
        return {
            "principal_amount": "1500000.00",
            "loan_purpose": "business",
            "loan_period_months": "6",
            "start_date": "2026-01-10",
            "application_notes": "Stock for my shop",
            "national_id": self._upload("national-id.pdf"),
            "collateral_security": self._upload("collateral.pdf"),
            "bank_statement": self._upload("bank-statement.pdf"),
        }

    @override_settings(
        DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
        SELF_SERVICE_LOAN_INTEREST_RATE=Decimal("10.00"),
    )
    @patch("cloudinary.models.uploader.upload_resource")
    @patch("apps.loans.views.send_loan_stage_notification_task.delay")
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_client_can_submit_self_service_application_with_required_documents(
        self, mock_applicant_delay, mock_stage_delay, mock_upload
    ):
        mock_upload.return_value = CloudinaryResource(
            public_id="loan-documents/test-file",
            resource_type="auto",
            type="upload",
            format="pdf",
        )
        self.web.force_login(self.user)

        response = self.web.post(reverse("loans:client_loan_apply"), self._post_data())

        loan = Loan.objects.get(borrower=self.borrower)
        self.assertRedirects(
            response, reverse("loans:client_loan_application_detail", args=[loan.id])
        )
        self.assertEqual(loan.status, "pending")
        self.assertEqual(loan.applied_by, self.user)
        self.assertEqual(loan.applied_by_role, "guest")
        self.assertEqual(loan.interest_rate, Decimal("10.00"))
        self.assertEqual(loan.documents.count(), 3)
        self.assertTrue(
            loan.documents.filter(
                document_type=LoanApplicationDocument.DOCUMENT_TYPE_NATIONAL_ID
            ).exists()
        )
        self.assertTrue(
            loan.documents.filter(
                document_type=LoanApplicationDocument.DOCUMENT_TYPE_COLLATERAL_SECURITY
            ).exists()
        )
        self.assertTrue(
            loan.documents.filter(document_type="bank_statement").exists()
        )
        mock_applicant_delay.assert_called_once()
        mock_stage_delay.assert_called_once_with(
            loan_id=loan.id,
            stage_status="pending",
            actor_name=self.user.username,
            base_url="http://testserver/",
        )

    @override_settings(
        DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage"
    )
    def test_missing_required_self_service_documents_is_rejected(self):
        self.web.force_login(self.user)
        data = {
            "principal_amount": "1500000.00",
            "loan_purpose": "business",
            "loan_period_months": "6",
            "start_date": "2026-01-10",
            "application_notes": "Stock for my shop",
        }

        response = self.web.post(reverse("loans:client_loan_apply"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Loan.objects.filter(borrower=self.borrower).exists())

    @override_settings(
        DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
        SELF_SERVICE_LOAN_INTEREST_RATE=Decimal("10.00"),
    )
    @patch("cloudinary.models.uploader.upload_resource")
    @patch("apps.loans.views.send_loan_stage_notification_task.delay")
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_client_cannot_apply_with_pending_or_running_loan(
        self, mock_applicant_delay, mock_stage_delay, mock_upload
    ):
        Loan.objects.create(
            borrower=self.borrower,
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("10.00"),
            start_date=date(2026, 1, 10),
            loan_period_months=6,
            status="pending",
            applied_by=self.user,
        )
        mock_upload.return_value = CloudinaryResource(
            public_id="loan-documents/test-file",
            resource_type="auto",
            type="upload",
            format="pdf",
        )
        self.web.force_login(self.user)

        response = self.web.post(reverse("loans:client_loan_apply"), self._post_data())

        self.assertRedirects(response, reverse("loans:client_loan_applications"))
        self.assertEqual(Loan.objects.filter(borrower=self.borrower).count(), 1)
        mock_applicant_delay.assert_not_called()
        mock_stage_delay.assert_not_called()

    def test_client_cannot_view_another_clients_application(self):
        self.web.force_login(self.user)
        other_loan = Loan.objects.create(
            borrower=self.other_client,
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("10.00"),
            start_date=date(2026, 1, 10),
            loan_period_months=6,
            status="pending",
            applied_by=self.other_user,
        )

        response = self.web.get(
            reverse("loans:client_loan_application_detail", args=[other_loan.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_client_application_list_renders_summary_layout(self):
        Loan.objects.create(
            borrower=self.borrower,
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("10.00"),
            start_date=date(2026, 1, 10),
            loan_period_months=6,
            status="pending",
            applied_by=self.user,
        )
        self.web.force_login(self.user)

        response = self.web.get(reverse("loans:client_loan_applications"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Loan self-service")
        self.assertContains(response, "Open Reviews")
        self.assertContains(response, "Application #")

    def test_client_document_open_redirects_to_attached_file(self):
        loan = Loan.objects.create(
            borrower=self.borrower,
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("10.00"),
            start_date=date(2026, 1, 10),
            loan_period_months=6,
            status="pending",
            applied_by=self.user,
        )
        document = LoanApplicationDocument.objects.create(
            loan=loan,
            document_type=LoanApplicationDocument.DOCUMENT_TYPE_NATIONAL_ID,
            file=CloudinaryResource(
                public_id="loan-documents/national-id",
                resource_type="auto",
                type="upload",
                format="pdf",
            ),
            uploaded_by=self.user,
        )
        self.web.force_login(self.user)

        response = self.web.get(
            reverse(
                "loans:client_loan_application_document_open",
                args=[loan.id, document.id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("loan-documents/national-id", response["Location"])

    def test_client_document_open_rejects_another_clients_document(self):
        other_loan = Loan.objects.create(
            borrower=self.other_client,
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("10.00"),
            start_date=date(2026, 1, 10),
            loan_period_months=6,
            status="pending",
            applied_by=self.other_user,
        )
        document = LoanApplicationDocument.objects.create(
            loan=other_loan,
            document_type=LoanApplicationDocument.DOCUMENT_TYPE_NATIONAL_ID,
            file=CloudinaryResource(
                public_id="loan-documents/other-national-id",
                resource_type="auto",
                type="upload",
                format="pdf",
            ),
            uploaded_by=self.other_user,
        )
        self.web.force_login(self.user)

        response = self.web.get(
            reverse(
                "loans:client_loan_application_document_open",
                args=[other_loan.id, document.id],
            )
        )

        self.assertEqual(response.status_code, 404)

    @override_settings(
        DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
        SELF_SERVICE_LOAN_INTEREST_RATE=Decimal("10.00"),
    )
    @patch("cloudinary.models.uploader.upload_resource")
    @patch("apps.loans.views.send_loan_stage_notification_task.delay")
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_staff_approval_workflow_accepts_self_service_loan(
        self, mock_applicant_delay, mock_stage_delay, mock_upload
    ):
        mock_upload.return_value = CloudinaryResource(
            public_id="loan-documents/test-file",
            resource_type="auto",
            type="upload",
            format="pdf",
        )
        self.web.force_login(self.user)
        self.web.post(reverse("loans:client_loan_apply"), self._post_data())
        loan = Loan.objects.get(borrower=self.borrower)

        self.assertEqual(loan.approve(self.boo), "boo_approved")
        self.assertEqual(loan.approve(self.hof), "hof_approved")
        self.assertEqual(loan.approve(self.ed), "approved")

        loan.refresh_from_db()
        self.assertEqual(loan.status, "approved")
        self.assertEqual(loan.documents.count(), 3)
