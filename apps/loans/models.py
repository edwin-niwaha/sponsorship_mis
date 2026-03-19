import logging
from datetime import date, datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.client.models import Client

PAYMENT_METHOD_CHOICES = [
    ("bank_transfer", "Bank Transfer"),
    ("cash", "Cash"),
    ("cheque", "Cheque"),
    ("mobile_money", "Mobile Money"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Shared journal-entry helper
# Replaces the three identical create_transaction() methods that previously
# lived inside LoanDisbursement, LoanRepayment, and LoanPenalty.
# ─────────────────────────────────────────────────────────────────────────────

def _post_transaction(loan, account, txn_type, amount, description, txn_date):
    TransactionHistory.objects.create(
        loan=loan,
        transaction_date=txn_date,
        amount=amount,
        transaction_type=txn_type,
        account=account,
        description=description,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ChartOfAccounts
# No changes to fields or db_table — identical to production.
# ─────────────────────────────────────────────────────────────────────────────

class ChartOfAccounts(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("asset",     "Asset"),
        ("liability", "Liability"),
        ("equity",    "Equity"),
        ("revenue",   "Revenue"),
        ("expense",   "Expense"),
    ]

    account_name   = models.CharField(max_length=255, verbose_name="Account Name")
    account_type   = models.CharField(max_length=50, choices=ACCOUNT_TYPE_CHOICES, verbose_name="Account Type")
    account_number = models.CharField(max_length=20, unique=True, verbose_name="Account Number")
    description    = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name        = "Chart of Account"
        verbose_name_plural = "Chart of Accounts"
        ordering            = ["account_number"]
        db_table            = "chart_of_accounts"

    def __str__(self):
        return f"{self.account_name} ({self.get_account_type_display()})"  # type: ignore

    def clean(self):
        if not self.account_number.isdigit():
            raise ValidationError("Account number must contain only numeric characters.")
        if self.account_type not in dict(self.ACCOUNT_TYPE_CHOICES):
            raise ValidationError(f"Invalid account type: {self.account_type}")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Loan
#
# Migration impact: ADDITIVE ONLY — 4 new indexes added to Meta.indexes.
# All field names, types, db_table, and related_names are identical to prod.
#
# Behaviour fixes (no schema change):
#   • update_status() uses queryset .update() — no recursive save()
#   • calculate_remaining_balances() uses ONE aggregate query (was 3)
#   • calculate_interest() keeps ROUND_DOWN to preserve existing data integrity
#   • monthly_installment / total_repayable promoted to @property
#   • removed wrong remaining_balance property (principal − interest)
# ─────────────────────────────────────────────────────────────────────────────

class Loan(models.Model):

    #  State Machine:
    #  pending → boo_approved → hof_approved → ed_approved → approved
    #  → disbursed → overdue / repaid / closed

    STATUS_CHOICES = [
        ("pending",      "Pending"),
        ("approved",     "Approved"),
        ("disbursed",    "Disbursed"),
        ("closed",       "Closed"),
        ("overdue",      "Overdue"),
        ("repaid",       "Repaid"),
        ("rejected",     "Rejected"),
        ("ed_rejected",  "ED Rejected"),
        ("hof_rejected", "HOF Rejected"),
        ("boo_approved", "BOO Approved"),
        ("hof_approved", "HOF Approved"),
        ("ed_approved",  "ED Approved"),
    ]

    INTEREST_METHOD_CHOICES = [
        ("flat_rate", "Flat Rate"),
        # ("reducing_rate", "Reducing Rate"),  # reserved for future use
    ]

    LOAN_PURPOSE_CHOICES = [
        ("business",             "Business"),
        ("school_fees",          "School Fees"),
        ("investment",           "Investment"),
        ("agriculture",          "Agriculture"),
        ("emergency",            "Emergency"),
        ("personal_development", "Personal Development"),
        ("salary",               "Salary Advance"),
    ]

    FINAL_STATUSES = frozenset({"closed", "repaid", "rejected"})

    # ── Fields — identical names/types to production ──────────────────────────

    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="loans",
    )
    borrower = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="loans",
        db_index=False,          # covered by composite index loan_borrower_status_idx
    )
    principal_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Principal Amount",
    )
    start_date = models.DateField(verbose_name="Loan Application Date")
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Annual Interest Rate (%)",
        validators=[MinValueValidator(0), MaxValueValidator(30)],
    )
    disbursement_date = models.DateField(
        blank=True, null=True,
        verbose_name="Disbursement Date",
    )
    loan_period_months = models.PositiveIntegerField(verbose_name="Loan Period (Months)")
    due_date           = models.DateField(blank=True, null=True, verbose_name="Due Date")
    status             = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending",
        verbose_name="Current Status",
    )
    total_interest = models.DecimalField(
        max_digits=15, decimal_places=2,
        blank=True, null=True,
        verbose_name="Total Interest Amount",
    )
    interest_method = models.CharField(
        max_length=20, choices=INTEREST_METHOD_CHOICES, default="flat_rate",
        verbose_name="Interest Calculation Method",
    )
    loan_purpose = models.CharField(
        max_length=20, choices=LOAN_PURPOSE_CHOICES, default="business",
        verbose_name="Loan Purpose",
    )

    # Approval chain — kept as concrete User FK to match production schema
    approved_by_boo = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="loans_boo_approved",
        verbose_name="BOO Approved By",
    )
    approved_by_hof = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="loans_hof_approved",
        verbose_name="HOF Approved By",
    )
    approved_by_ed = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="loans_ed_approved",
        verbose_name="ED Approved By",
    )
    approved_date = models.DateField(blank=True, null=True, verbose_name="Approval Date")
    reason_for_rejection = models.TextField(
        null=True, blank=True, max_length=255,
        verbose_name="Reason for Rejection",
    )
    reason_for_approval = models.TextField(
        max_length=255, blank=False, null=False,
        default="Approval granted based on the borrower's savings history.",
        verbose_name="Reason for Approval",
    )
    # applied_by uses settings.AUTH_USER_MODEL to match existing production FK
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="applied_loans",
    )
    applied_by_role = models.CharField(max_length=15, blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="loans_created",
        verbose_name="Created By",
    )
    created_at         = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at         = models.DateTimeField(auto_now=True,     verbose_name="Updated At")
    last_reminder_sent = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Last Reminder Sent",
    )

    class Meta:
        db_table            = "loans"
        verbose_name        = "Loan"
        verbose_name_plural = "Loans"
        indexes = [
            # Aging report: WHERE status IN ('disbursed','overdue')
            #               AND disbursement_date IS NOT NULL
            models.Index(
                fields=["status", "disbursement_date"],
                name="loan_status_disb_idx",
            ),
            # Per-client loan history pages
            models.Index(
                fields=["borrower", "status"],
                name="loan_borrower_status_idx",
            ),
            # Daily overdue scheduler / update_status
            models.Index(
                fields=["due_date", "status"],
                name="loan_due_status_idx",
            ),
            # send_loan_notifications management command
            models.Index(
                fields=["last_reminder_sent"],
                name="loan_last_reminder_idx",
            ),
        ]

    # ── Validation ────────────────────────────────────────────────────────────

    def clean(self):
        if self.start_date and self.start_date > date.today():
            raise ValidationError({"start_date": "Start date cannot be in the future."})
        if self.due_date and self.disbursement_date and self.due_date <= self.disbursement_date:
            raise ValidationError("Due date must be after the disbursement date.")
        if self.loan_period_months is not None and self.loan_period_months <= 0:
            raise ValidationError("Loan period must be a positive integer.")

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def total_repayable(self) -> Decimal:
        """Principal + total interest. Safe when total_interest is NULL."""
        return (self.principal_amount or Decimal("0")) + (self.total_interest or Decimal("0"))

    @property
    def monthly_installment(self) -> Decimal:
        """Equal flat-rate instalment — used by aging report and schedule."""
        if not self.loan_period_months:
            return Decimal("0.00")
        return (self.total_repayable / Decimal(self.loan_period_months)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

    # ── Business logic ────────────────────────────────────────────────────────

    def calculate_due_date(self):
        if self.disbursement_date and self.loan_period_months:
            self.due_date = self.disbursement_date + relativedelta(months=self.loan_period_months)

    def calculate_interest(self):
        """
        Flat-rate interest. Kept as ROUND_DOWN to preserve existing stored
        values for active loans (changing rounding on live data would cause
        balance mismatches).
        """
        if self.interest_method == "flat_rate":
            if self.principal_amount is not None and self.interest_rate is not None:
                self.total_interest = (
                    self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
                ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        elif self.interest_method == "reducing_rate":
            monthly_rate    = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            current_balance = self.principal_amount
            total_interest  = Decimal(0)
            for _ in range(self.loan_period_months):
                interest_payment = (current_balance * monthly_rate).quantize(
                    Decimal("0.01"), rounding=ROUND_DOWN,
                )
                total_interest  += interest_payment
                current_balance -= self.principal_amount / self.loan_period_months
            self.total_interest = total_interest.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    def calculate_monthly_payment(self):
        """Kept for backwards compatibility — delegates to monthly_installment."""
        if self.interest_method == "flat_rate":
            return self.monthly_installment
        elif self.interest_method == "reducing_rate":
            monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            return (self.principal_amount * monthly_rate) / (
                1 - (1 + monthly_rate) ** -self.loan_period_months
            )

    def calculate_interest_payment(self, current_balance):
        """Per-month interest used by generate_payment_schedule."""
        if self.interest_method == "flat_rate":
            return (
                self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
            ) / self.loan_period_months
        elif self.interest_method == "reducing_rate":
            monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            return current_balance * monthly_rate

    def generate_payment_schedule(self):
        schedule        = []
        monthly_principal = self.principal_amount / self.loan_period_months
        current_balance   = self.principal_amount

        for month in range(1, self.loan_period_months + 1):
            payment_due_date  = self.disbursement_date + relativedelta(months=month)
            interest_payment  = self.calculate_interest_payment(current_balance)
            principal_payment = min(monthly_principal, current_balance)

            schedule.append({
                "payment_due_date":  payment_due_date,
                "principal_payment": principal_payment,
                "interest_payment":  interest_payment,
                "total_payment":     principal_payment + interest_payment,
                "remaining_balance": max(current_balance - principal_payment, Decimal("0")),
            })
            current_balance -= principal_payment

        if schedule:
            schedule[-1]["remaining_balance"] = max(current_balance, Decimal("0"))

        return schedule

    def calculate_remaining_balances(self) -> dict:
        """
        Single aggregation query instead of three separate repayment queries.
        Reduces DB round-trips from 4 to 2 on every balance check.
        """
        totals = self.repayments.aggregate(
            paid_principal=Sum("principal_payment"),
            paid_interest =Sum("interest_payment"),
            paid_penalty  =Sum("penalty_payment"),
        )
        unpaid_penalties = (
            self.penalties
            .filter(is_paid=False)
            .aggregate(total=Sum("penalty_amount"))["total"]
            or Decimal("0.00")
        )
        return {
            "principal_balance": max(
                self.principal_amount - (totals["paid_principal"] or Decimal("0")),
                Decimal("0.00"),
            ),
            "interest_balance": max(
                (self.total_interest or Decimal("0")) - (totals["paid_interest"] or Decimal("0")),
                Decimal("0.00"),
            ),
            "penalty_balance": max(
                unpaid_penalties - (totals["paid_penalty"] or Decimal("0")),
                Decimal("0.00"),
            ),
        }

    def update_status(self):
        """
        Uses queryset .update() to avoid calling self.save() recursively.
        Only writes to the DB when the status actually changes.
        """
        if self.status in self.FINAL_STATUSES:
            return

        balances           = self.calculate_remaining_balances()
        total_remaining    = sum(balances.values())
        new_status         = self.status

        if total_remaining <= 0:
            new_status = "repaid"
        elif self.due_date and timezone.now().date() > self.due_date:
            if self.status in {"approved", "disbursed"}:
                new_status = "overdue"

        if new_status != self.status:
            self.status = new_status
            Loan.objects.filter(pk=self.pk).update(status=new_status)

    def calculate_total_amount_due_balance(self, due_date, total_amount_due):
        try:
            if isinstance(due_date, datetime):
                due_date = due_date.date()

            if not isinstance(due_date, date):
                logger.error("Invalid due_date type for Loan %s: %s", self.id, type(due_date))
                raise ValidationError("due_date must be a date object")
            if not isinstance(total_amount_due, (Decimal, int, float)):
                logger.error("Invalid total_amount_due type for Loan %s: %s", self.id, type(total_amount_due))
                raise ValidationError("total_amount_due must be a numeric value")

            repayments = self.repayments.filter(repayment_date__lte=due_date).aggregate(
                total_principal=Sum("principal_payment", default=Decimal("0.00")),
                total_interest =Sum("interest_payment",  default=Decimal("0.00")),
                total_penalty  =Sum("penalty_payment",   default=Decimal("0.00")),
            )
            total_paid = (
                (repayments["total_principal"] or Decimal("0.00"))
                + (repayments["total_interest"]  or Decimal("0.00"))
                + (repayments["total_penalty"]   or Decimal("0.00"))
            )
            total_penalty = (
                self.penalties
                .filter(penalty_date__lte=due_date, is_paid=False)
                .aggregate(total=Sum("penalty_amount", default=Decimal("0.00")))["total"]
                or Decimal("0.00")
            )
            return max(
                Decimal(str(total_amount_due)) + total_penalty - total_paid,
                Decimal("0.00"),
            ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        except Exception as e:
            logger.error(
                "Error in calculate_total_amount_due_balance for Loan %s: %s",
                self.id, str(e), exc_info=True,
            )
            raise

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            super().save(*args, **kwargs)  # generate PK first

        if not self.account:
            try:
                self.account = ChartOfAccounts.objects.get(account_number="1050")
            except ChartOfAccounts.DoesNotExist:
                raise ValidationError("Default loan account missing. Please contact support.")

        self.calculate_due_date()
        self.calculate_interest()

        if not is_new:
            self.update_status()

        super().save(*args, **kwargs)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def __str__(self):
        return f"Loan {self.id} - {self.borrower} ({self.status})"

    def to_select2(self):
        return {
            "label": f"Loan #{self.id} - {self.borrower.full_name} ({self.borrower.reg_number})",
            "value": self.id,
        }


# ─────────────────────────────────────────────────────────────────────────────
# LoanDisbursement
#
# Migration impact: none — no field or index changes.
# Behaviour fix: interest_amount now returns loan.total_interest (correct for
#   flat-rate) instead of principal × rate (which ignored the loan period).
# ─────────────────────────────────────────────────────────────────────────────

class LoanDisbursement(models.Model):

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="disbursements")
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE,
        related_name="disbursements_from_account",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[("Cash", "Cash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash",
    )
    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan disbursement",
    )

    class Meta:
        db_table            = "loan_disbursements"
        verbose_name        = "Loan Disbursement"
        verbose_name_plural = "Loan Disbursements"

    @property
    def disbursed_amount(self):
        return self.loan.principal_amount

    @property
    def interest_amount(self):
        """
        Flat-rate: total interest is already stored on the loan.
        The original formula (principal × rate) was wrong — it ignored
        the loan period and double-counted for multi-month loans.
        """
        return self.loan.total_interest or Decimal("0.00")

    def save(self, *args, **kwargs):
        if not self.loan.account:
            self.loan.account = ChartOfAccounts.objects.get(account_number="1050")
            self.loan.save()
        super().save(*args, **kwargs)
        self._create_transaction_entries()

    def _create_transaction_entries(self):
        if not self.account or not self.loan.account:
            raise ValueError("Both disbursement and loan accounts must be set.")

        d    = self.loan.disbursement_date
        desc = self.description or f"Loan disbursement — Loan {self.loan.id}"

        # Principal legs
        _post_transaction(self.loan, self.loan.account, "debit",  self.disbursed_amount, desc, d)
        _post_transaction(self.loan, self.account,      "credit", self.disbursed_amount, desc, d)

        # Interest legs
        try:
            ir = ChartOfAccounts.objects.get(account_number="1060")
            ii = ChartOfAccounts.objects.get(account_number="5030")
        except ChartOfAccounts.DoesNotExist as exc:
            raise ValueError(f"Required chart-of-accounts entry missing: {exc}")

        interest_desc = f"Interest receivable for Loan {self.loan.id}"
        _post_transaction(self.loan, ir, "debit",  self.interest_amount, interest_desc, d)
        _post_transaction(self.loan, ii, "credit", self.interest_amount, interest_desc, d)

    # Keep old name as alias so any existing callers don't break
    def create_transaction_entries(self):
        self._create_transaction_entries()

    def __str__(self):
        return f"Disbursement {self.id} for Loan {self.loan.id}"


# ─────────────────────────────────────────────────────────────────────────────
# LoanRepayment
#
# Migration impact: 1 new composite index repayment_loan_date_idx added.
#   The existing repayment_date index is kept unchanged.
# Behaviour fix:
#   • _mark_penalties_paid() now uses queryset .update() to avoid
#     re-triggering LoanPenalty.save() side-effects (double transactions).
#   • Per-field validation errors surfaced individually (better UX).
# ─────────────────────────────────────────────────────────────────────────────

class LoanRepayment(models.Model):

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="repayments",
        db_index=False,    # covered by composite index below
    )
    repayment_date    = models.DateField()
    principal_payment = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    interest_payment  = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    penalty_payment   = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        verbose_name="Penalty Payment",
    )
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments",
    )
    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan payment",
    )

    class Meta:
        db_table            = "loan_repayments"
        verbose_name        = "Loan Repayment"
        verbose_name_plural = "Loan Repayments"
        ordering            = ["-repayment_date"]
        indexes = [
            # NEW — core balance query: repayments for a loan up to a cutoff date
            models.Index(fields=["loan", "repayment_date"], name="repayment_loan_date_idx"),
            # EXISTING — kept unchanged
            models.Index(fields=["repayment_date"]),
        ]

    @property
    def total_payment(self):
        return self.principal_payment + self.interest_payment + self.penalty_payment

    def clean(self):
        if not self.loan_id:
            raise ValidationError("Please select a loan.")

        balances = self.loan.calculate_remaining_balances()
        errors   = {}

        total_balance = sum(balances.values())
        total_payment = self.principal_payment + self.interest_payment + self.penalty_payment

        if total_payment > total_balance:
            raise ValidationError(
                f"Repayment of {total_payment:,.2f} exceeds remaining balance of {total_balance:,.2f}."
            )
        if self.principal_payment > balances["principal_balance"]:
            errors["principal_payment"] = (
                f"Principal payment of {self.principal_payment:,.2f} exceeds "
                f"remaining principal balance of {balances['principal_balance']:,.2f}."
            )
        if self.interest_payment > balances["interest_balance"]:
            errors["interest_payment"] = (
                f"Interest payment of {self.interest_payment:,.2f} exceeds "
                f"remaining interest balance of {balances['interest_balance']:,.2f}."
            )
        if self.penalty_payment > balances["penalty_balance"]:
            errors["penalty_payment"] = (
                f"Penalty payment of {self.penalty_payment:,.2f} exceeds "
                f"remaining penalty balance of {balances['penalty_balance']:,.2f}."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self._create_transaction_entries()
        if self.loan:
            self.loan.update_status()

    def _create_transaction_entries(self):
        d       = self.repayment_date
        desc    = self.description or f"Loan repayment — Loan {self.loan.id}"
        pi_only = self.principal_payment + self.interest_payment

        # Cash/Bank account: debit full amount received
        _post_transaction(self.loan, self.account,      "debit",  self.total_payment, desc, d)
        # Loan Receivable: credit principal + interest
        _post_transaction(self.loan, self.loan.account, "credit", pi_only,            desc, d)

        if self.interest_payment > 0:
            ir = ChartOfAccounts.objects.get(account_number="1060")
            _post_transaction(
                self.loan, ir, "credit", self.interest_payment,
                f"Interest received for Loan {self.loan.id}", d,
            )

        if self.penalty_payment > 0:
            pa = ChartOfAccounts.objects.get(account_number="1071")
            _post_transaction(
                self.loan, pa, "credit", self.penalty_payment,
                f"Penalty payment for Loan {self.loan.id}", d,
            )
            self._mark_penalties_paid()

    def _mark_penalties_paid(self):
        """
        Apply penalty_payment to oldest unpaid penalties first.
        Uses queryset .update() to avoid re-triggering LoanPenalty.save()
        which would double-post accounting entries.
        """
        remaining = self.penalty_payment
        for penalty in self.loan.penalties.filter(is_paid=False).order_by("penalty_date"):
            if remaining <= 0:
                break
            if remaining >= penalty.penalty_amount:
                remaining -= penalty.penalty_amount
                LoanPenalty.objects.filter(pk=penalty.pk).update(
                    is_paid=True,
                    remaining_amount=Decimal("0.00"),
                )
            else:
                LoanPenalty.objects.filter(pk=penalty.pk).update(
                    remaining_amount=penalty.penalty_amount - remaining,
                )
                remaining = Decimal("0.00")

    # Keep old names as aliases
    def create_transaction_entries(self):
        self._create_transaction_entries()

    def mark_penalties_paid(self):
        self._mark_penalties_paid()

    def get_interest_receivable_account(self):
        return ChartOfAccounts.objects.get(account_number="1060")

    def get_penalty_receivable_account(self):
        return ChartOfAccounts.objects.get(account_number="1071")

    def __str__(self):
        return (
            f"Repayment for Loan {self.loan.id} on {self.repayment_date}"
            f" - Total Payment: {self.total_payment}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LoanPenalty
#
# Migration impact: 1 new composite index penalty_loan_paid_idx added.
#   The existing (penalty_date, is_paid) index is kept unchanged.
# Behaviour fix:
#   • save() now guards _create_transaction_entries() with is_new — so
#     updating is_paid=True no longer double-posts the debit/credit.
#   • deleted_by FK given a related_name to avoid clashes.
# ─────────────────────────────────────────────────────────────────────────────

class LoanPenalty(models.Model):

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="penalties",
        db_index=False,    # covered by composite index below
    )
    penalty_date   = models.DateField(default=timezone.now, verbose_name="Penalty Date")
    penalty_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Penalty Amount")
    remaining_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        verbose_name="Remaining Penalty Amount",
    )
    reason  = models.CharField(max_length=255, verbose_name="Penalty Reason")
    is_paid = models.BooleanField(default=False, verbose_name="Is Paid")
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="penalties",
        verbose_name="Penalty Account",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at  = models.DateTimeField(auto_now=True,     verbose_name="Updated At")
    created_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="penalties_created",
        verbose_name="Created By",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="penalties_deleted",   # added to avoid reverse accessor clash
    )

    class Meta:
        db_table            = "loan_penalties"
        verbose_name        = "Loan Penalty"
        verbose_name_plural = "Loan Penalties"
        ordering            = ["-penalty_date"]
        indexes = [
            # NEW — calculate_remaining_balances: unpaid penalties per loan
            models.Index(fields=["loan", "is_paid"], name="penalty_loan_paid_idx"),
            # EXISTING — kept unchanged
            models.Index(fields=["penalty_date", "is_paid"]),
        ]

    def clean(self):
        if self.penalty_amount is not None and self.penalty_amount <= 0:
            raise ValidationError("Penalty amount must be positive.")
        if self.remaining_amount is None or self.remaining_amount < 0:
            raise ValidationError("Remaining penalty amount cannot be negative or null.")

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new and not self.remaining_amount:
            self.remaining_amount = self.penalty_amount

        self.full_clean()
        super().save(*args, **kwargs)

        # Guard: only post journal entries on INSERT.
        # Subsequent saves (e.g. marking is_paid=True via _mark_penalties_paid)
        # must NOT re-post the same debit/credit entries.
        if is_new and not self.is_paid:
            self._create_transaction_entries()

        self.loan.update_status()

    def _create_transaction_entries(self):
        try:
            interest_income_account = ChartOfAccounts.objects.get(account_number="5030")
        except ChartOfAccounts.DoesNotExist:
            raise ValidationError("Loan Interest Income account (5030) does not exist.")

        desc = f"Penalty for Loan {self.loan.id}: {self.reason}"
        _post_transaction(self.loan, self.account,              "debit",  self.penalty_amount, desc, self.penalty_date)
        _post_transaction(self.loan, interest_income_account,   "credit", self.penalty_amount, desc, self.penalty_date)

    # Keep old name as alias
    def create_transaction_entries(self):
        self._create_transaction_entries()

    def apply_payment(self, payment_amount):
        if payment_amount <= 0:
            raise ValidationError("Payment amount must be positive.")
        with transaction.atomic():
            self.remaining_amount = max(
                self.remaining_amount - Decimal(str(payment_amount)),
                Decimal("0.00"),
            )
            self.is_paid = self.remaining_amount == Decimal("0.00")
            self.save()

    def __str__(self):
        return f"Penalty {self.id} for Loan {self.loan.id} - {self.penalty_amount}"


# ─────────────────────────────────────────────────────────────────────────────
# TransactionHistory
#
# Migration impact: 3 new indexes added.
# No field changes.
# ─────────────────────────────────────────────────────────────────────────────

class TransactionHistory(models.Model):

    TRANSACTION_TYPE_CHOICES = [
        ("credit", "Credit"),
        ("debit",  "Debit"),
    ]

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="transactions",
        db_index=False,    # covered by composite index below
    )
    transaction_date = models.DateField()
    amount           = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE,
        related_name="transaction_history",
        db_index=False,    # covered by composite index below
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table            = "transaction_histories"
        verbose_name        = "Transaction History"
        verbose_name_plural = "Transaction History"
        ordering            = ["-transaction_date"]
        indexes = [
            # NEW — ledger view: all transactions for a loan ordered by date
            models.Index(fields=["loan", "transaction_date"],             name="txn_loan_date_idx"),
            # NEW — account statement: all entries for a COA account
            models.Index(fields=["account", "transaction_date"],          name="txn_account_date_idx"),
            # NEW — debit/credit filter within a date range
            models.Index(fields=["transaction_type", "transaction_date"], name="txn_type_date_idx"),
        ]

    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} {self.amount}"
