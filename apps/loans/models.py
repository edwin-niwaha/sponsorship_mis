from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_DOWN
from django.utils import timezone
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
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

# class Loan(models.Model):
#     # Loan status options
#     STATUS_CHOICES = [
#         ("pending", "Pending"),
#         ("approved", "Approved"),
#         ("disbursed", "Disbursed"),
#         ("closed", "Closed"),
#         ("overdue", "Overdue"),
#         ("repaid", "Repaid"),
#         ("rejected", "Rejected"),
#     ]

#     # Interest calculation methods
#     INTEREST_METHOD_CHOICES = [
#         ("flat_rate", "Flat Rate"),
#         ("reducing_rate", "Reducing Rate"),
#     ]

#     # Fields
#     account = models.ForeignKey(
#         ChartOfAccounts,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="loans",
#     )
#     borrower = models.ForeignKey(
#         Client,
#         on_delete=models.CASCADE,
#         related_name="loans",
#     )
#     principal_amount = models.DecimalField(
#         max_digits=15,
#         decimal_places=2,
#         verbose_name="Principal Amount",
#     )
#     interest_rate = models.DecimalField(
#         max_digits=5,
#         decimal_places=2,
#         verbose_name="Annual Interest Rate (%)",
#     )
#     start_date = models.DateField(verbose_name="Start Date")
#     loan_period_months = models.PositiveIntegerField(
#         verbose_name="Loan Period (Months)"
#     )
#     due_date = models.DateField(blank=True, null=True, verbose_name="Due Date")
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default="pending",
#         verbose_name="Current Status",
#     )
#     total_interest = models.DecimalField(
#         max_digits=15,
#         decimal_places=2,
#         blank=True,
#         null=True,
#         verbose_name="Total Interest Amount",
#     )
#     interest_method = models.CharField(
#         max_length=20,
#         choices=INTEREST_METHOD_CHOICES,
#         default="flat_rate",
#         verbose_name="Interest Calculation Method",
#     )
#     approved_by = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name="Approved By",
#     )
#     approved_date = models.DateField(
#         blank=True, null=True, verbose_name="Approval Date"
#     )
#     created_by = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="loans_created",
#         verbose_name="Created By",
#     )
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
#     updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

#     class Meta:
#         db_table = "loans"
#         verbose_name = "Loan"
#         verbose_name_plural = "Loans"

#     def clean(self):
#         """Validate the loan period and due date."""
#         if self.due_date and self.due_date <= self.start_date:
#             raise ValidationError("Due date must be after the start date.")
#         if self.loan_period_months <= 0:
#             raise ValidationError("Loan period must be a positive integer.")

#     def calculate_due_date(self):
#         """Calculate and set the due date based on the start date and loan period."""
#         if self.start_date and self.loan_period_months:
#             self.due_date = self.start_date + relativedelta(
#                 months=self.loan_period_months
#             )

#     def calculate_interest(self):
#         """Calculate total interest based on the interest method (flat or reducing)."""
#         if self.interest_method == "flat_rate":
#             self.total_interest = (
#                 self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
#             ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
#         elif self.interest_method == "reducing_rate":
#             monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
#             current_balance = self.principal_amount
#             total_interest = Decimal(0)

#             for month in range(self.loan_period_months):
#                 interest_payment = (current_balance * monthly_rate).quantize(
#                     Decimal("0.01"), rounding=ROUND_DOWN
#                 )
#                 total_interest += interest_payment
#                 principal_payment = self.principal_amount / self.loan_period_months
#                 current_balance -= principal_payment

#             self.total_interest = total_interest.quantize(
#                 Decimal("0.01"), rounding=ROUND_DOWN
#             )

#     def calculate_monthly_payment(self):
#         """Calculate the monthly payment based on the interest method."""
#         if self.interest_method == "flat_rate":
#             total_payment = self.principal_amount + self.total_interest
#             return total_payment / self.loan_period_months
#         elif self.interest_method == "reducing_rate":
#             monthly_interest_rate = (
#                 Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
#             )
#             return (self.principal_amount * monthly_interest_rate) / (
#                 1 - (1 + monthly_interest_rate) ** -self.loan_period_months
#             )

#     def generate_payment_schedule(self):
#         """Generate a detailed monthly payment schedule for the loan."""
#         schedule = []
#         monthly_payment = self.calculate_monthly_payment()
#         monthly_principal_payment = self.principal_amount / self.loan_period_months
#         current_balance = self.principal_amount

#         for month in range(1, self.loan_period_months + 1):
#             payment_due_date = self.start_date + relativedelta(months=month)
#             interest_payment = self.calculate_interest_payment(current_balance)
#             principal_payment = monthly_principal_payment

#             if principal_payment > current_balance:
#                 principal_payment = current_balance

#             schedule.append(
#                 {
#                     "payment_due_date": payment_due_date,
#                     "principal_payment": principal_payment,
#                     "interest_payment": interest_payment,
#                     "total_payment": principal_payment + interest_payment,
#                     "remaining_balance": current_balance - principal_payment,
#                 }
#             )

#             current_balance -= principal_payment

#         if current_balance < 0:
#             current_balance = 0
#         if schedule:
#             schedule[-1]["remaining_balance"] = current_balance

#         return schedule

#     def calculate_interest_payment(self, current_balance):
#         """Calculate interest payment for a specific month based on balance and interest method."""
#         if self.interest_method == "flat_rate":
#             total_interest = (
#                 self.principal_amount * Decimal(self.interest_rate) / Decimal(100)
#             )
#             return total_interest / self.loan_period_months
#         elif self.interest_method == "reducing_rate":
#             monthly_rate = Decimal(self.interest_rate) / Decimal(100) / Decimal(12)
#             return current_balance * monthly_rate

#     def calculate_remaining_balances(self):
#         """Calculate remaining principal and interest based on total repayments."""
#         # Get total principal repaid from repayments
#         total_repaid = self.repayments.aggregate(total=Sum("principal_payment"))[
#             "total"
#         ] or Decimal("0.00")

#         # Get total interest paid from repayments
#         total_interest_paid = self.repayments.aggregate(total=Sum("interest_payment"))[
#             "total"
#         ] or Decimal("0.00")

#         # Calculate remaining balances
#         principal_balance = max(self.principal_amount - total_repaid, Decimal("0.00"))
#         interest_balance = max(
#             self.total_interest - total_interest_paid, Decimal("0.00")
#         )

#         return {
#             "principal_balance": principal_balance,
#             "interest_balance": interest_balance,
#         }

#     def update_status(self):
#         """Update loan status based on remaining balance and due date."""
#         if self.remaining_balance <= 0:
#             self.status = "repaid"
#         elif timezone.now().date() > self.due_date:
#             self.status = "overdue" if self.status == "approved" else self.status

#     def save(self, *args, **kwargs):
#         """Override save to ensure the account is set, calculate due date, interest, and status before saving."""
#         if not self.account:
#             try:
#                 self.account = ChartOfAccounts.objects.get(
#                     account_number="1050"  # Loan Receivable
#                 )
#             except ChartOfAccounts.DoesNotExist:
#                 raise ValidationError(
#                     "It seems that the default loan account is missing. "
#                     "Please contact support to ensure the 'Loan Receivable' exists in the system."
#                 )

#         if not self.due_date:
#             self.calculate_due_date()
#         if not self.total_interest:
#             self.calculate_interest()
#         self.update_status()

#         super().save(*args, **kwargs)

#     @property
#     def remaining_balance(self):
#         return (
#             self.calculate_remaining_balances()["principal_balance"]
#             + self.calculate_remaining_balances()["interest_balance"]
#         )

#     def __str__(self):
#         return f"Loan {self.id} - {self.borrower} ({self.status})"


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
        max_digits=15,
        decimal_places=2,
        verbose_name="Principal Amount",
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Annual Interest Rate (%)",
    )
    start_date = models.DateField(verbose_name="Start Date")
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
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Approved By",
    )
    approved_date = models.DateField(
        blank=True, null=True, verbose_name="Approval Date"
    )
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
        monthly_payment = self.calculate_monthly_payment()
        monthly_principal_payment = self.principal_amount / self.loan_period_months
        current_balance = self.principal_amount

        for month in range(1, self.loan_period_months + 1):
            payment_due_date = self.start_date + relativedelta(months=month)
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

        # Calculate remaining balances
        principal_balance = max(self.principal_amount - total_repaid, Decimal("0.00"))
        interest_balance = max(
            self.total_interest - total_interest_paid, Decimal("0.00")
        )

        return {
            "principal_balance": principal_balance,
            "interest_balance": interest_balance,
        }

    def save(self, *args, **kwargs):
        """Override save to ensure the account is set, calculate due date, interest, and status before saving."""
        if not self.account:
            try:
                self.account = ChartOfAccounts.objects.get(
                    account_number="1050"
                )  # Loan Receivable
            except ChartOfAccounts.DoesNotExist:
                raise ValidationError(
                    "Default loan account missing. Please contact support."
                )

        self.calculate_due_date()
        self.calculate_interest()
        super().save(*args, **kwargs)

    @property
    def remaining_balance(self):
        return self.principal_amount - self.total_interest  # Simplified for example

    def __str__(self):
        return f"Loan {self.id} - {self.borrower} ({self.status})"


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

    class Meta:
        db_table = "loan_disbursements"
        verbose_name = "Loan Disbursement"
        verbose_name_plural = "Loan Disbursements"
        ordering = ["disbursement_date"]

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
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments"
    )
    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan payment"
    )

    @property
    def total_payment(self):
        """Calculate the total payment amount (principal + interest)."""
        return self.principal_payment + self.interest_payment

    class Meta:
        db_table = "loan_repayments"
        verbose_name = "Loan Repayment"
        verbose_name_plural = "Loan Repayments"
        ordering = ["-repayment_date"]

    def clean(self):
        """Validate repayment amount and ensure it does not exceed total loan balance."""
        if not self.loan:
            raise ValidationError("Please select a loan.")

        # Calculate remaining balances
        balances = self.loan.calculate_remaining_balances()
        remaining_principal = balances[
            "principal_balance"
        ]  # Adjusted based on your method's return structure
        remaining_interest = balances[
            "interest_balance"
        ]  # Adjusted based on your method's return structure

        total_balance = remaining_principal + remaining_interest
        total_payment = self.principal_payment + self.interest_payment

        if total_payment > total_balance:
            raise ValidationError(
                f"Repayment exceeds remaining balance of {total_balance:,.2f}."
            )

        if self.principal_payment > remaining_principal:
            raise ValidationError(
                f"Principal payment of {self.principal_payment:,.2f} exceeds remaining principal balance."
            )

        if self.interest_payment > remaining_interest:
            raise ValidationError(
                f"Interest payment of {self.interest_payment:,.2f} exceeds remaining interest balance."
            )

    def save(self, *args, **kwargs):
        """Override save method to perform validation and balance update."""
        self.full_clean()  # Ensure all validations are run
        super().save(*args, **kwargs)  # Call the parent's save method
        self.create_transaction_entries()  # Record transactions

    def create_transaction_entries(self):
        """Create entries for the repayment, including interest receivable if applicable."""
        # Create a transaction for the loan repayment
        self.create_transaction(
            self.account, "debit", self.total_payment, self.description
        )
        self.create_transaction(
            self.loan.account, "credit", self.total_payment, self.description
        )

        # Handle interest payment if applicable
        if self.interest_payment > 0:
            interest_receivable_account = self.get_interest_receivable_account()
            self.create_transaction(
                account=interest_receivable_account,
                transaction_type="credit",
                amount=self.interest_payment,
                description=f"Interest received for Loan {self.loan.id}",
            )

    def get_interest_receivable_account(self):
        """Retrieve the interest receivable account, or raise an error if not found."""
        return ChartOfAccounts.objects.get(account_number="1060")

    def create_transaction(self, account, transaction_type, amount, description):
        """Helper to create a transaction entry."""
        TransactionHistory.objects.create(
            loan=self.loan,
            transaction_date=self.repayment_date,
            amount=amount,
            transaction_type=transaction_type,
            account=account,
            description=description,
        )

    def __str__(self):
        return f"Repayment for Loan {self.loan.id} on {self.repayment_date} - Total Payment: {self.total_payment}"
