from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cloudinary import CloudinaryResource
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as DjangoTestClient
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.client.models import Client
from apps.users.models import Profile

from .models import (
    ChartOfAccounts,
    Loan,
    LoanApplicationDocument,
    LoanDisbursement,
    LoanPenalty,
    LoanRepayment,
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
            account_name="Interest Receivable", account_type="asset", account_number="1060"
        )
        ChartOfAccounts.objects.create(
            account_name="Penalty Receivable", account_type="asset", account_number="1071"
        )
        ChartOfAccounts.objects.create(
            account_name="Interest Income", account_type="revenue", account_number="5030"
        )
        self.client = Client.objects.create(full_name="Jane Doe", reg_number="C001")
        self.boo = self._user("boo-user", "boo")
        self.hof = self._user("hof-user", "hof")
        self.ed = self._user("ed-user", "ed")

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

    def _approved_loan(self):
        loan = self._loan()
        loan.approve(self.boo)
        loan.approve(self.hof)
        loan.approve(self.ed)
        loan.refresh_from_db()
        return loan

    def test_loan_approval_chain_sets_audit_fields(self):
        loan = self._loan()

        self.assertEqual(loan.approve(self.boo), "boo_approved")
        self.assertEqual(loan.approved_by_boo, self.boo)
        self.assertEqual(loan.approve(self.hof), "hof_approved")
        self.assertEqual(loan.approved_by_hof, self.hof)
        self.assertEqual(loan.approve(self.ed), "approved")
        self.assertEqual(loan.approved_by_ed, self.ed)
        self.assertEqual(loan.approved_date, timezone.localdate())

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

        self.assertEqual(loan.calculate_remaining_balances()["penalty_balance"], Decimal("60.00"))

    def test_standard_aging_bucket_inputs(self):
        loan = self._approved_loan()
        loan.disburse(date(2026, 1, 1))
        LoanDisbursement.objects.create(loan=loan, account=self.cash)

        aging = compute_installment_based_days_overdue(loan, date(2026, 3, 15))

        self.assertGreater(aging["days_overdue"], 0)
        self.assertGreater(aging["shortfall"], Decimal("0.00"))


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
            account_name="Interest Receivable", account_type="asset", account_number="1060"
        )
        ChartOfAccounts.objects.create(
            account_name="Penalty Receivable", account_type="asset", account_number="1071"
        )
        ChartOfAccounts.objects.create(
            account_name="Interest Income", account_type="revenue", account_number="5030"
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
        return SimpleUploadedFile(name, b"test file content", content_type="application/pdf")

    def _post_data(self):
        return {
            "principal_amount": "1500000.00",
            "loan_purpose": "business",
            "loan_period_months": "6",
            "start_date": "2026-01-10",
            "application_notes": "Stock for my shop",
            "national_id": self._upload("national-id.pdf"),
            "collateral_security": self._upload("collateral.pdf"),
        }

    @override_settings(
        DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
        SELF_SERVICE_LOAN_INTEREST_RATE=Decimal("10.00"),
    )
    @patch("cloudinary.models.uploader.upload_resource")
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_client_can_submit_self_service_application_with_required_documents(self, mock_delay, mock_upload):
        mock_upload.return_value = CloudinaryResource(
            public_id="loan-documents/test-file",
            resource_type="auto",
            type="upload",
            format="pdf",
        )
        self.web.force_login(self.user)

        response = self.web.post(reverse("loans:client_loan_apply"), self._post_data())

        loan = Loan.objects.get(borrower=self.borrower)
        self.assertRedirects(response, reverse("loans:client_loan_application_detail", args=[loan.id]))
        self.assertEqual(loan.status, "pending")
        self.assertEqual(loan.applied_by, self.user)
        self.assertEqual(loan.applied_by_role, "guest")
        self.assertEqual(loan.interest_rate, Decimal("10.00"))
        self.assertEqual(loan.documents.count(), 2)
        self.assertTrue(
            loan.documents.filter(document_type=LoanApplicationDocument.DOCUMENT_TYPE_NATIONAL_ID).exists()
        )
        self.assertTrue(
            loan.documents.filter(document_type=LoanApplicationDocument.DOCUMENT_TYPE_COLLATERAL_SECURITY).exists()
        )
        self.assertEqual(mock_delay.call_count, 2)

    @override_settings(DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage")
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
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_client_cannot_apply_with_pending_or_running_loan(self, mock_delay, mock_upload):
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
        mock_delay.assert_not_called()

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

        response = self.web.get(reverse("loans:client_loan_application_detail", args=[other_loan.id]))

        self.assertEqual(response.status_code, 404)

    @override_settings(
        DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
        SELF_SERVICE_LOAN_INTEREST_RATE=Decimal("10.00"),
    )
    @patch("cloudinary.models.uploader.upload_resource")
    @patch("apps.loans.views.send_loan_application_email_task.delay")
    def test_staff_approval_workflow_accepts_self_service_loan(self, mock_delay, mock_upload):
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
        self.assertEqual(loan.documents.count(), 2)
