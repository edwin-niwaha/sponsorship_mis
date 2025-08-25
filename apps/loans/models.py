from datetime import date
from decimal import ROUND_DOWN, Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum, Q
from django.utils import timezone

import logging

logger = logging.getLogger(__name__)

from apps.client.models import Client

PAYMENT_METHOD_CHOICES = [
    ("bank_transfer", "Bank Transfer"),
    ("cash", "Cash"),
    ("cheque", "Cheque"),
    ("mobile_money", "Mobile Money"),
]


# =================================== ChartOfAccounts Model ===================================
class ChartOfAccounts(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ]

    account_name = models.CharField(max_length=255, verbose_name="Account Name")
    account_type = models.CharField(
        max_length=50, choices=ACCOUNT_TYPE_CHOICES, verbose_name="Account Type"
    )
    account_number = models.CharField(
        max_length=20, unique=True, verbose_name="Account Number"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name = "Chart of Account"
        verbose_name_plural = "Chart of Accounts"
        ordering = ["account_number"]
        db_table = "chart_of_accounts"

    def __str__(self):
        return f"{self.account_name} ({self.get_account_type_display()})"

    def clean(self):
        # Validate that the account number is numeric
        if not self.account_number.isdigit():
            raise ValidationError(
                "Account number must contain only numeric characters."
            )

        # Ensure that the account type is a valid choice
        if self.account_type not in dict(self.ACCOUNT_TYPE_CHOICES).keys():
            raise ValidationError(f"Invalid account type: {self.account_type}")

        # Additional custom validations can be added here if necessary

    def save(self, *args, **kwargs):
        # Run the clean method before saving
        self.clean()
        super().save(*args, **kwargs)


# =================================== Loan Model ===================================
class Loan(models.Model):
    # Loan status options
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("disbursed", "Disbursed"),
        ("closed", "Closed"),
        ("overdue", "Overdue"),
        ("repaid", "Repaid"),
        ("rejected", "Rejected"),
        ("ed_rejected", "ED Rejected"),
        ("hof_rejected", "HOF Rejected"),
        ("boo_approved", "BOO Approved"),  # New status
        ("hof_approved", "HOF Approved"),  # New status
        ("ed_approved", "ED Approved"),  # New status
    ]

    # Interest calculation methods
    INTEREST_METHOD_CHOICES = [
        ("flat_rate", "Flat Rate"),
        #
        #  ("reducing_rate", "Reducing Rate"),
    ]
    # Loan purpose options
    LOAN_PURPOSE_CHOICES = [
        ("business", "Business"),
        ("school_fees", "School Fees"),
        ("investment", "Investment"),
        ("agriculture", "Agriculture"),
        ("emergency", "Emergency"),
        ("personal_development", "Personal Development"),
        ("salary", "Salary Advance"),
    ]
    # Fields
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans",
    )
    borrower = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    principal_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Principal Amount",
    )
    start_date = models.DateField(verbose_name="Loan Application Date")
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Annual Interest Rate (%)",
        validators=[
            MinValueValidator(0),  # Ensures the value is not negative
            MaxValueValidator(30),  # Ensures the value does not exceed 30
        ],
    )
    disbursement_date = models.DateField(
        blank=True, null=True, verbose_name="Disbursement Date"
    )
    loan_period_months = models.PositiveIntegerField(
        verbose_name="Loan Period (Months)"
    )
    due_date = models.DateField(blank=True, null=True, verbose_name="Due Date")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Current Status",
    )
    total_interest = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Total Interest Amount",
    )
    interest_method = models.CharField(
        max_length=20,
        choices=INTEREST_METHOD_CHOICES,
        default="flat_rate",
        verbose_name="Interest Calculation Method",
    )
    loan_purpose = models.CharField(
        max_length=20,
        choices=LOAN_PURPOSE_CHOICES,
        default="business",
        verbose_name="Loan Purpose",
    )

    approved_by_boo = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_boo_approved",
        verbose_name="BOO Approved By",
    )
    approved_by_hof = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_hof_approved",
        verbose_name="HOF Approved By",
    )
    approved_by_ed = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_ed_approved",
        verbose_name="ED Approved By",
    )
    approved_date = models.DateField(
        blank=True, null=True, verbose_name="Approval Date"
    )
    reason_for_rejection = models.TextField(
        null=True,
        blank=True,
        verbose_name="Reason for Rejection",
        max_length=255,
    )
    reason_for_approval = models.TextField(
        max_length=255,
        blank=False,
        null=False,
        verbose_name="Reason for Approval",
        default="Approval granted based on the borrower's savings history.",
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="applied_loans",
    )
    applied_by_role = models.CharField(max_length=15, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_created",
        verbose_name="Created By",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "loans"
        verbose_name = "Loan"
        verbose_name_plural = "Loans"

    def clean(self):
        # Ensure the start date is not in the future
        if self.start_date > date.today():
            raise ValidationError({"start_date": "Start date cannot be in the future."})

        """Validate the loan period and due date."""
        if self.due_date and self.due_date <= self.disbursement_date:
            raise ValidationError("Due date must be after the start date.")

        if self.loan_period_months <= 0:
            raise ValidationError("Loan period must be a positive integer.")

    def calculate_due_date(self):
        """Calculate and set the due date based on the start date and loan period."""
        if self.disbursement_date and self.loan_period_months:
            self.due_date = self.disbursement_date + relativedelta(
                months=self.loan_period_months
            )

    def calculate_interest(self):
        """Calculate total interest based on the interest method (flat or reducing)."""
        if self.interest_method == "flat_rate":
            self.total_interest = (
                self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
            ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        elif self.interest_method == "reducing_rate":
            monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            current_balance = self.principal_amount
            total_interest = Decimal(0)

            for month in range(self.loan_period_months):
                interest_payment = (current_balance * monthly_rate).quantize(
                    Decimal("0.01"), rounding=ROUND_DOWN
                )
                total_interest += interest_payment
                principal_payment = self.principal_amount / self.loan_period_months
                current_balance -= principal_payment

            self.total_interest = total_interest.quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )

    def calculate_monthly_payment(self):
        """Calculate the monthly payment based on the interest method."""
        if self.interest_method == "flat_rate":
            total_payment = self.principal_amount + self.total_interest
            return total_payment / self.loan_period_months
        elif self.interest_method == "reducing_rate":
            monthly_interest_rate = (
                Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            )
            return (self.principal_amount * monthly_interest_rate) / (
                1 - (1 + monthly_interest_rate) ** -self.loan_period_months
            )

    def generate_payment_schedule(self):
        """Generate a detailed monthly payment schedule for the loan."""
        schedule = []
        self.calculate_monthly_payment()
        monthly_principal_payment = self.principal_amount / self.loan_period_months
        current_balance = self.principal_amount

        for month in range(1, self.loan_period_months + 1):
            payment_due_date = self.disbursement_date + relativedelta(months=month)
            interest_payment = self.calculate_interest_payment(current_balance)
            principal_payment = monthly_principal_payment

            if principal_payment > current_balance:
                principal_payment = current_balance

            schedule.append(
                {
                    "payment_due_date": payment_due_date,
                    "principal_payment": principal_payment,
                    "interest_payment": interest_payment,
                    "total_payment": principal_payment + interest_payment,
                    "remaining_balance": current_balance - principal_payment,
                }
            )

            current_balance -= principal_payment

        if current_balance < 0:
            current_balance = 0
        if schedule:
            schedule[-1]["remaining_balance"] = current_balance

        return schedule

    def calculate_interest_payment(self, current_balance):
        """Calculate interest payment for a specific month based on balance and interest method."""
        if self.interest_method == "flat_rate":
            total_interest = (
                self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
            )
            return total_interest / self.loan_period_months
        elif self.interest_method == "reducing_rate":
            monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            return current_balance * monthly_rate

    def calculate_remaining_balances(self):
        """Calculate remaining principal and interest based on total repayments."""
        # Get total principal repaid from repayments
        total_repaid = self.repayments.aggregate(total=Sum("principal_payment"))[
            "total"
        ] or Decimal("0.00")
        # Get total interest paid from repayments
        total_interest_paid = self.repayments.aggregate(total=Sum("interest_payment"))[
            "total"
        ] or Decimal("0.00")
        total_penalty_paid = self.repayments.aggregate(total=Sum("penalty_payment"))[
            "total"
        ] or Decimal("0.00")

        # Calculate remaining balances
        principal_balance = max(self.principal_amount - total_repaid, Decimal("0.00"))
        interest_balance = max(
            self.total_interest - total_interest_paid, Decimal("0.00")
        )
        penalty_balance = max(
            self.penalties.filter(is_paid=False).aggregate(total=Sum("penalty_amount"))[
                "total"
            ]
            or Decimal("0.00"),
            Decimal("0.00"),
        )

        return {
            "principal_balance": principal_balance,
            "interest_balance": interest_balance,
            "penalty_balance": penalty_balance,
        }

    def update_status(self):
        """Update loan status based on current status, balance, and due date."""
        # Calculate total remaining balance
        balances = self.calculate_remaining_balances()
        total_remaining_balance = (
            balances["principal_balance"]
            + balances["interest_balance"]
            + balances["penalty_balance"]
        )

        # Status transitions based on remaining balance, due date, and current status
        if self.status in ["closed", "repaid", "rejected"]:
            # No changes for final statuses
            return

        if total_remaining_balance <= 0:
            # If fully repaid, set status to "repaid"
            self.status = "repaid"
        elif self.due_date and timezone.now().date() > self.due_date:
            # If due date has passed and balance remains, set to "overdue"
            if self.status in ["approved", "disbursed"]:
                self.status = "overdue"
        elif self.status == "pending":
            # "pending" remains until manually approved
            pass
        elif self.status == "approved":
            # If approved but not disbursed, check for overdue
            if self.due_date and timezone.now().date() > self.due_date:
                self.status = "overdue"

    def save(self, *args, **kwargs):
        """Override save to ensure account setup and perform initial calculations before saving."""
        # Check if this is the first time the object is being saved (object doesn't have a primary key yet)
        is_new_instance = self.pk is None

        if is_new_instance:
            super().save(*args, **kwargs)  # Save initially to generate primary key

        # Set the default account only after the first save, when pk is available
        if not self.account:
            try:
                self.account = ChartOfAccounts.objects.get(
                    account_number="1050"
                )  # Loan Receivable
            except ChartOfAccounts.DoesNotExist:
                raise ValidationError(
                    "Default loan account missing. Please contact support."
                )

        # Recalculate due date and interest
        self.calculate_due_date()
        self.calculate_interest()

        # Update status based on remaining balance and due date, but only if it's not a new instance
        if not is_new_instance:
            self.update_status()

        # Final save with all fields updated
        super().save(*args, **kwargs)

    @property
    def remaining_balance(self):
        return self.principal_amount - self.total_interest  # Simplified for example

    def __str__(self):
        return f"Loan {self.id} - {self.borrower} ({self.status})"

    def to_select2(self):
        # Format the label to include client information (full name, registration number, etc.)
        return {
            "label": f"Loan #{self.id} - {self.borrower.full_name} ({self.borrower.reg_number})",
            "value": self.id,
        }

    # def calculate_total_amount_due_balance(self, due_date, total_amount_due):
    #     # Get repayments made on or before the due date
    #     repayments = self.repayments.filter(repayment_date__lte=due_date).aggregate(
    #         total_principal=Sum("principal_payment"),
    #         total_interest=Sum("interest_payment"),
    #         total_penalty=Sum("penalty_payment"),
    #     )

    #     total_principal_paid = repayments["total_principal"] or Decimal("0.00")
    #     total_interest_paid = repayments["total_interest"] or Decimal("0.00")
    #     total_penalty_paid = repayments["total_penalty"] or Decimal("0.00")
    #     total_paid = total_principal_paid + total_interest_paid + total_penalty_paid

    #     # Calculate remaining due balance
    #     total_penalty = self.penalties.filter(
    #         penalty_date__lte=due_date, is_paid=False
    #     ).aggregate(total=Sum("penalty_amount"))["total"] or Decimal("0.00")

    #     remaining_due_balance = max(
    #         total_amount_due + total_penalty - total_paid, Decimal("0.00")
    #     )
    #     return remaining_due_balance.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    def calculate_total_amount_due_balance(self, due_date, total_amount_due):
        try:
            # Ensure due_date is a date object
            if isinstance(due_date, datetime):
                due_date = due_date.date()

            # Validate input parameters
            if not isinstance(due_date, date):
                logger.error(f"Invalid due_date type for Loan {self.id}: {type(due_date)}")
                raise ValidationError("due_date must be a date object")
            if not isinstance(total_amount_due, (Decimal, int, float)):
                logger.error(f"Invalid total_amount_due type for Loan {self.id}: {type(total_amount_due)}")
                raise ValidationError("total_amount_due must be a numeric value")

            # Get repayments made on or before the due date
            repayments = self.repayments.filter(
                repayment_date__lte=due_date,
                principal_payment__isnull=False,
                interest_payment__isnull=False,
                penalty_payment__isnull=False
            ).aggregate(
                total_principal=Sum("principal_payment", default=Decimal("0.00")),
                total_interest=Sum("interest_payment", default=Decimal("0.00")),
                total_penalty=Sum("penalty_payment", default=Decimal("0.00")),
            )

            total_principal_paid = repayments["total_principal"] or Decimal("0.00")
            total_interest_paid = repayments["total_interest"] or Decimal("0.00")
            total_penalty_paid = repayments["total_penalty"] or Decimal("0.00")
            total_paid = total_principal_paid + total_interest_paid + total_penalty_paid

            # Calculate penalties up to the due date
            total_penalty = self.penalties.filter(
                penalty_date__lte=due_date,
                is_paid=False,
                penalty_amount__isnull=False
            ).aggregate(
                total=Sum("penalty_amount", default=Decimal("0.00"))
            )["total"] or Decimal("0.00")

            # Calculate remaining due balance
            remaining_due_balance = max(
                total_amount_due + total_penalty - total_paid, Decimal("0.00")
            )
            return remaining_due_balance.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        except Exception as e:
            logger.error(f"Error in calculate_total_amount_due_balance for Loan {self.id}: {str(e)}", exc_info=True)
            raise

# =================================== LoanDisbursement Model ===================================
class LoanDisbursement(models.Model):
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="disbursements"
    )
    # disbursement_date = models.DateField(default=timezone.now)
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.CASCADE,
        related_name="disbursements_from_account",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[("Cash", "Cash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash",
    )
    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan disbursement"
    )

    class Meta:
        db_table = "loan_disbursements"
        verbose_name = "Loan Disbursement"
        verbose_name_plural = "Loan Disbursements"

    @property
    def disbursed_amount(self):
        """Return the principal amount from the associated Loan."""
        return self.loan.principal_amount

    @property
    def interest_amount(self):
        """Calculate the interest amount based on the loan's interest rate and principal."""
        interest_rate = self.loan.interest_rate / 100  # Convert percentage to decimal
        return (
            self.disbursed_amount * interest_rate
        )  # Modify as necessary for time periods

    def save(self, *args, **kwargs):
        # Ensure the loan has a specific account assigned
        if not self.loan.account:
            self.loan.account = ChartOfAccounts.objects.get(
                account_number="1050"  # Replace with actual account name if different
            )
            self.loan.save()

        # Proceed with saving the disbursement and creating transactions
        super().save(*args, **kwargs)
        self.create_transaction_entries()

    def create_transaction_entries(self):
        """Create transaction entries for both loan and disbursement accounts."""
        if not self.account or not self.loan.account:
            raise ValueError(
                "Both disbursement and loan accounts must be set before creating transactions."
            )

        # Debit the Loan Receivable Account for the principal
        self.create_transaction(
            account=self.loan.account,  # Loan Receivable account
            transaction_type="debit",
            amount=self.disbursed_amount,
            description=self.description,
        )

        # Credit the Cash (or Bank) Account for the principal
        self.create_transaction(
            account=self.account,  # Cash or Bank account
            transaction_type="credit",
            amount=self.disbursed_amount,
            description=self.description,
        )

        # Get the Loan Interest Receivable Account for the interest amount
        try:
            interest_receivable_account = ChartOfAccounts.objects.get(
                account_number="1060"  # Loan Interest Receivable
            )
        except ChartOfAccounts.DoesNotExist:
            raise ValueError("Loan Interest Receivable account does not exist.")

        # Debit the Loan Interest Receivable Account for the interest amount
        self.create_transaction(
            account=interest_receivable_account,  # Use the specific Receivable account for Loan Interest Receivable
            transaction_type="debit",
            amount=self.interest_amount,
            description=f"Interest receivable for Loan {self.loan.id}",
        )

        # Get the Loan Interest Income Account for the interest amount
        try:
            interest_income_account = ChartOfAccounts.objects.get(
                account_number="5030"  # Loan Interest Income
            )
        except ChartOfAccounts.DoesNotExist:
            raise ValueError("Loan Interest Income account does not exist.")

        # Credit the Loan Interest Income Account for the interest amount
        self.create_transaction(
            account=interest_income_account,  # Use the specific income account for Loan Interest
            transaction_type="credit",
            amount=self.interest_amount,
            description=f"Loan interest income for Loan {self.loan.id}",
        )

    def create_transaction(self, account, transaction_type, amount, description):
        """Helper to create a transaction history entry."""
        TransactionHistory.objects.create(
            loan=self.loan,
            transaction_date=self.loan.disbursement_date,
            amount=amount,
            transaction_type=transaction_type,
            account=account,
            description=description,  # Store the description
        )

    def __str__(self):
        return f"Disbursement {self.id} for Loan {self.loan.id}"


# =================================== TransactionHistory Model ===================================
class TransactionHistory(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="transaction_history"
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "transaction_histories"
        ordering = ["-transaction_date"]
        verbose_name = "Transaction History"
        verbose_name_plural = "Transaction History"

    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} {self.amount}"


# =================================== LoanRepayment Model ===================================
class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    repayment_date = models.DateField()
    principal_payment = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    interest_payment = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    penalty_payment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Penalty Payment",
    )
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments"
    )
    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan payment"
    )

    @property
    def total_payment(self):
        return self.principal_payment + self.interest_payment + self.penalty_payment

    class Meta:
        db_table = "loan_repayments"
        verbose_name = "Loan Repayment"
        verbose_name_plural = "Loan Repayments"
        ordering = ["-repayment_date"]

    def clean(self):
        if not self.loan:
            raise ValidationError("Please select a loan.")

        balances = self.loan.calculate_remaining_balances()
        remaining_principal = balances["principal_balance"]
        remaining_interest = balances["interest_balance"]
        remaining_penalty = balances["penalty_balance"]

        total_balance = remaining_principal + remaining_interest + remaining_penalty
        total_payment = (
            self.principal_payment + self.interest_payment + self.penalty_payment
        )

        if total_payment > total_balance:
            raise ValidationError(
                f"Repayment exceeds remaining balance of {total_balance:,.2f}."
            )

        if self.principal_payment > remaining_principal:
            raise ValidationError(
                f"Principal payment of {self.principal_payment:,.2f} exceeds remaining principal balance of {remaining_principal:,.2f}."
            )

        if self.interest_payment > remaining_interest:
            raise ValidationError(
                f"Interest payment of {self.interest_payment:,.2f} exceeds remaining interest balance of {remaining_interest:,.2f}."
            )

        if self.penalty_payment > remaining_penalty:
            raise ValidationError(
                f"Penalty payment of {self.penalty_payment:,.2f} exceeds remaining penalty balance of {remaining_penalty:,.2f}."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.create_transaction_entries()
        if self.loan:
            self.loan.update_status()

    def create_transaction_entries(self):
        self.create_transaction(
            self.account,
            "debit",
            self.principal_payment + self.interest_payment + self.penalty_payment,
            self.description,
        )
        self.create_transaction(
            self.loan.account,
            "credit",
            self.principal_payment + self.interest_payment,
            self.description,
        )

        if self.interest_payment > 0:
            interest_receivable_account = self.get_interest_receivable_account()
            self.create_transaction(
                account=interest_receivable_account,
                transaction_type="credit",
                amount=self.interest_payment,
                description=f"Interest received for Loan {self.loan.id}",
            )

        if self.penalty_payment > 0:
            penalty_receivable_account = self.get_penalty_receivable_account()
            self.create_transaction(
                account=penalty_receivable_account,
                transaction_type="credit",
                amount=self.penalty_payment,
                description=f"Penalty payment for Loan {self.loan.id}",
            )
            self.mark_penalties_paid()

    def create_transaction(self, account, transaction_type, amount, description):
        """Helper to create a transaction entry for the repayment."""
        TransactionHistory.objects.create(
            loan=self.loan,
            transaction_date=self.repayment_date,
            amount=amount,
            transaction_type=transaction_type,
            account=account,
            description=description,
        )

    def get_interest_receivable_account(self):
        return ChartOfAccounts.objects.get(account_number="1060")

    def get_penalty_receivable_account(self):
        return ChartOfAccounts.objects.get(account_number="1071")

    def mark_penalties_paid(self):
        remaining_payment = self.penalty_payment
        unpaid_penalties = self.loan.penalties.filter(is_paid=False).order_by(
            "penalty_date"
        )

        for penalty in unpaid_penalties:
            if remaining_payment >= penalty.penalty_amount:
                penalty.is_paid = True
                penalty.save()
                remaining_payment -= penalty.penalty_amount
            else:
                break

    def __str__(self):
        return f"Repayment for Loan {self.loan.id} on {self.repayment_date} - Total Payment: {self.total_payment}"


# =================================== LoanPenalty Model ===================================


class LoanPenalty(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="penalties")
    penalty_date = models.DateField(default=timezone.now, verbose_name="Penalty Date")
    penalty_amount = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="Penalty Amount"
    )
    remaining_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Remaining Penalty Amount",
        default=Decimal("0.00"),
    )
    reason = models.CharField(max_length=255, verbose_name="Penalty Reason")
    is_paid = models.BooleanField(default=False, verbose_name="Is Paid")
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.CASCADE,
        related_name="penalties",
        verbose_name="Penalty Account",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="penalties_created",
        verbose_name="Created By",
    )

    class Meta:
        db_table = "loan_penalties"
        verbose_name = "Loan Penalty"
        verbose_name_plural = "Loan Penalties"
        ordering = ["-penalty_date"]

    def clean(self):
        if self.penalty_amount <= 0:
            raise ValidationError("Penalty amount must be positive.")
        if self.remaining_amount is None or self.remaining_amount < 0:
            raise ValidationError(
                "Remaining penalty amount cannot be negative or null."
            )

    def save(self, *args, **kwargs):
        # Set remaining_amount for new penalties
        if not self.pk and not self.remaining_amount:
            self.remaining_amount = self.penalty_amount

        self.full_clean()
        super().save(*args, **kwargs)

        if not self.is_paid:
            self.create_transaction_entries()
        self.loan.update_status()

    def apply_payment(self, payment_amount):
        """Apply a payment to this penalty and update its status."""
        if payment_amount <= 0:
            raise ValidationError("Payment amount must be positive.")

        with transaction.atomic():
            self.remaining_amount -= payment_amount
            if self.remaining_amount <= 0:
                self.remaining_amount = Decimal("0.00")
                self.is_paid = True
            self.save()

    def create_transaction_entries(self):
        """Create the debit and credit transactions for this penalty."""
        # Debit the Penalty Receivable Account (1071)
        self.create_transaction(
            account=self.account,
            transaction_type="debit",
            amount=self.penalty_amount,
            description=f"Penalty for Loan {self.loan.id}: {self.reason}",
        )

        # Credit the Loan Interest Income Account (5030)
        try:
            interest_income_account = ChartOfAccounts.objects.get(account_number="5030")
        except ChartOfAccounts.DoesNotExist:
            raise ValidationError("Loan Interest Income account (5030) does not exist.")

        self.create_transaction(
            account=interest_income_account,
            transaction_type="credit",
            amount=self.penalty_amount,
            description=f"Penalty income for Loan {self.loan.id}: {self.reason}",
        )

    def create_transaction(self, account, transaction_type, amount, description):
        TransactionHistory.objects.create(
            loan=self.loan,
            transaction_date=self.penalty_date,
            amount=amount,
            transaction_type=transaction_type,
            account=account,
            description=description,
        )

    def __str__(self):
        return f"Penalty {self.id} for Loan {self.loan.id} - {self.penalty_amount}"
