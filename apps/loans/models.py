from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_DOWN
from django.utils import timezone
from django.db import models
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
    ]

    # Interest calculation methods
    INTEREST_METHOD_CHOICES = [
        ("flat_rate", "Flat Rate"),
        ("reducing_rate", "Reducing Rate"),
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
        max_digits=10,
        decimal_places=2,
        verbose_name="Principal Amount",  # Total loan amount
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Annual Interest Rate (%)",  # Annual interest rate in percentage
    )
    start_date = models.DateField(verbose_name="Start Date")  # Loan start date
    loan_period_months = models.PositiveIntegerField(
        verbose_name="Loan Period (Months)"  # Duration of loan in months
    )
    due_date = models.DateField(
        blank=True, null=True, verbose_name="Due Date"  # Loan due date
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Current Status",  # Current status
    )
    remaining_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Remaining Balance",  # Remaining balance
    )
    total_interest = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Total Interest Amount",  # Total interest amount
    )
    interest_method = models.CharField(
        max_length=20,
        choices=INTEREST_METHOD_CHOICES,
        default="flat_rate",
        verbose_name="Interest Calculation Method",
    )

    class Meta:
        verbose_name = "Loan"
        verbose_name_plural = "Loans"

    def clean(self):
        """Validate the loan period and due date."""
        if self.due_date and self.due_date <= self.start_date:
            raise ValidationError("Due date must be after the start date.")
        if self.loan_period_months <= 0:
            raise ValidationError("Loan period must be a positive integer.")

    def calculate_due_date(self):
        """Calculate and set the due date based on the start date and loan period."""
        if self.start_date and self.loan_period_months:
            self.due_date = self.start_date + relativedelta(
                months=self.loan_period_months
            )

    def calculate_interest(self):
        """Calculate total interest based on the interest method (flat or reducing)."""
        if self.interest_method == "flat_rate":
            # Flat rate total interest is constant based on principal amount and interest rate
            self.total_interest = (
                self.principal_amount * (Decimal(self.interest_rate) / Decimal(100))
            ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        elif self.interest_method == "reducing_rate":
            # Reducing rate calculation
            monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            current_balance = self.principal_amount
            total_interest = Decimal(0)

            # Calculate interest on the declining balance for each month
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

        return self.total_interest

    def calculate_monthly_payment(self):
        """Calculate the monthly payment based on the interest method."""
        if not all(
            [self.principal_amount, self.interest_rate, self.loan_period_months]
        ):
            raise ValueError(
                "Principal amount, interest rate, and loan period must be provided."
            )

        if self.interest_method == "flat_rate":
            total_interest = (
                self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
            )
            total_payment = self.principal_amount + total_interest
            return total_payment / self.loan_period_months
        elif self.interest_method == "reducing_rate":
            monthly_interest_rate = (
                Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            )
            return (self.principal_amount * monthly_interest_rate) / (
                1 - (1 + monthly_interest_rate) ** -self.loan_period_months
            )
        else:
            raise ValueError("Invalid interest method.")

    def generate_payment_schedule(self):
        """Generate a detailed monthly payment schedule for the loan."""
        schedule = []
        monthly_payment = self.calculate_monthly_payment()
        monthly_principal_payment = self.principal_amount / self.loan_period_months
        current_balance = self.principal_amount

        for month in range(1, self.loan_period_months + 1):
            payment_due_date = self.start_date + relativedelta(months=month)

            # Calculate interest payment for this month
            interest_payment = self.calculate_interest_payment(current_balance)

            # Use the fixed principal payment
            principal_payment = monthly_principal_payment

            # Ensure principal payment does not exceed current balance
            if principal_payment > current_balance:
                principal_payment = current_balance

            # Append monthly details to schedule
            schedule.append(
                {
                    "payment_due_date": payment_due_date,
                    "principal_payment": principal_payment,
                    "interest_payment": interest_payment,
                    "total_payment": principal_payment + interest_payment,
                    "remaining_balance": current_balance - principal_payment,
                }
            )

            # Update current balance
            current_balance -= principal_payment

        # Final balance check
        if current_balance < 0:
            current_balance = 0  # Ensure balance doesn't go negative
        if schedule:
            schedule[-1]["remaining_balance"] = current_balance

        return schedule

    def calculate_interest_payment(self, current_balance):
        """Calculate interest payment for a specific month based on balance and interest method."""
        if self.interest_method == "flat_rate":
            total_interest = (
                self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
            )
            monthly_interest_payment = total_interest / self.loan_period_months
            return monthly_interest_payment  # Fixed interest payment each month for flat rate

        elif self.interest_method == "reducing_rate":
            monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
            return current_balance * monthly_rate

        return 0

    def update_status(self):
        """Update loan status based on remaining balance and due date."""
        if self.remaining_balance is not None and self.remaining_balance <= 0:
            self.status = "repaid"
        elif timezone.now().date() > self.due_date:
            self.status = "overdue" if self.status == "approved" else self.status

    def save(self, *args, **kwargs):
        """Override save to ensure the account is set, calculate due date, interest, and status before saving."""
        if not self.account:
            try:
                self.account = ChartOfAccounts.objects.get(
                    account_name="Loan Receivable"
                )
            except ChartOfAccounts.DoesNotExist:
                raise ValidationError(
                    "It seems that the default loan account is missing. "
                    "Please contact support to ensure the 'Loan Receivable' exists in the system."
                )

        # Calculate due date, interest, and update status
        if not self.due_date:
            self.calculate_due_date()
        if self.remaining_balance is None:
            self.remaining_balance = self.principal_amount
        if not self.total_interest:
            self.calculate_interest()
        self.update_status()

        super().save(*args, **kwargs)

    def __str__(self):
        """String representation of the Loan model."""
        return f"Loan {self.id} - {self.borrower} ({self.status})"

    @property
    def disbursement_date(self):
        return (
            self.loandisbursement.disbursement_date
            if hasattr(self, "loandisbursement")
            else None
        )


# =================================== LoanDisbursement Model ===================================
class LoanDisbursement(models.Model):
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="disbursements"
    )
    disbursement_date = models.DateField()
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="disbursements"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[("Cash", "Cash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash",
    )
    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan disbursement"
    )

    @property
    def disbursed_amount(self):
        """Return the principal amount from the associated Loan."""
        return self.loan.principal_amount

    def save(self, *args, **kwargs):
        # Ensure the loan has a specific account assigned
        if not self.loan.account:
            self.loan.account = ChartOfAccounts.objects.get(
                name="Loan Receivable"  # Replace with actual account name if different
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

        # Debit the Loan Receivable Account
        self.create_transaction(
            account=self.loan.account,  # Loan Receivable account
            transaction_type="debit",
            amount=self.disbursed_amount,
            description=self.description,
        )

        # Credit the Cash (or Bank) Account
        self.create_transaction(
            account=self.account,  # Cash or Bank account
            transaction_type="credit",
            amount=self.disbursed_amount,
            description=self.description,
        )

    def create_transaction(self, account, transaction_type, amount, description):
        """Helper to create a transaction history entry."""
        TransactionHistory.objects.create(
            loan=self.loan,
            transaction_date=self.disbursement_date,
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
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="transaction_history"
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} {self.amount}"


# =================================== Product Model ===================================
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    max_loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    min_loan_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


# =================================== LoanProduct Model ===================================
class LoanProduct(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return f"Loan Product for Loan {self.loan.id} - {self.product.name}"


# =================================== LoanRepayment Model ===================================
class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    repayment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments"
    )

    def clean(self):
        # Check if repayment amount exceeds the remaining balance
        if self.amount > self.loan.remaining_balance:
            raise ValidationError(
                "Repayment amount cannot exceed the remaining balance."
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # Validate before saving
        super().save(*args, **kwargs)
        self.create_repayment_transaction_entries()
        self.update_loan_balance_and_status()

    def create_repayment_transaction_entries(self):
        """Create debit and credit entries for the loan repayment."""
        try:
            TransactionHistory.objects.bulk_create(
                [
                    # Debit the payment account
                    TransactionHistory(
                        loan=self.loan,
                        transaction_date=self.repayment_date,
                        amount=self.amount,
                        transaction_type="debit",
                        account=self.account,
                    ),
                    # Credit the loan account
                    TransactionHistory(
                        loan=self.loan,
                        transaction_date=self.repayment_date,
                        amount=self.amount,
                        transaction_type="credit",
                        account=self.loan.account,
                    ),
                ]
            )
        except Exception as e:
            raise ValidationError(f"Error creating transaction entries: {e}")

    def update_loan_balance_and_status(self):
        """Update the loan's remaining balance and status after repayment."""
        # Reduce remaining balance by the repayment amount
        self.loan.remaining_balance -= self.amount
        self.loan.remaining_balance = max(
            self.loan.remaining_balance, 0
        )  # Avoid negative balance

        # Update loan status if fully repaid
        if self.loan.remaining_balance == 0:
            self.loan.status = "repaid"
        elif timezone.now().date() > self.loan.due_date:
            self.loan.status = "overdue"

        self.loan.save(update_fields=["remaining_balance", "status"])

    def __str__(self):
        return f"Repayment for Loan {self.loan.id} on {self.repayment_date} - Amount: {self.amount}"
