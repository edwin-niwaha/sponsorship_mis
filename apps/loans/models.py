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
    remaining_principal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Remaining Principal Balance",
    )
    remaining_interest = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Remaining Interest Balance",
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

    def update_status(self):
        """Update loan status based on remaining balance and due date."""
        if self.remaining_balance <= 0:
            self.status = "repaid"
        elif timezone.now().date() > self.due_date:
            self.status = "overdue" if self.status == "approved" else self.status

    def save(self, *args, **kwargs):
        """Override save to ensure the account is set, calculate due date, interest, and status before saving."""
        if not self.account:
            try:
                self.account = ChartOfAccounts.objects.get(
                    account_number="1050"  # Loan Receivable
                )
            except ChartOfAccounts.DoesNotExist:
                raise ValidationError(
                    "It seems that the default loan account is missing. "
                    "Please contact support to ensure the 'Loan Receivable' exists in the system."
                )

        if not self.due_date:
            self.calculate_due_date()
        if not self.remaining_principal:
            self.remaining_principal = self.principal_amount
        if not self.remaining_interest:
            self.calculate_interest()
            self.remaining_interest = self.total_interest
        self.update_status()

        super().save(*args, **kwargs)

    @property
    def remaining_balance(self):
        return (self.remaining_principal or Decimal(0)) + (
            self.remaining_interest or Decimal(0)
        )

    def __str__(self):
        return f"Loan {self.id} - {self.borrower} ({self.status})"


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

    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} {self.amount}"


# =================================== LoanRepayment Model ===================================
# class LoanRepayment(models.Model):
#     loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
#     repayment_date = models.DateField()
#     amount = models.DecimalField(
#         max_digits=10, decimal_places=2, default=Decimal("0.00")
#     )  # Ensure default value
#     account = models.ForeignKey(
#         ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments"
#     )
#     description = models.CharField(
#         max_length=255, blank=True, null=True, default="Loan payment"
#     )

#     def clean(self):
#         # Ensure amount is not None and initialize if necessary
#         if self.amount is None:
#             self.amount = Decimal("0.00")

#         # Retrieve current balances or set them to zero if None
#         remaining_principal = self.loan.remaining_principal or Decimal("0.00")
#         remaining_interest = self.loan.remaining_interest or Decimal("0.00")

#         # Calculate total remaining balance
#         total_remaining_balance = remaining_principal + remaining_interest

#         # Check if repayment amount exceeds the total remaining balance
#         if self.amount > total_remaining_balance:
#             raise ValidationError(
#                 f"Repayment amount of {self.amount:,.2f} exceeds the total remaining balance of {total_remaining_balance:,.2f}."
#             )

#         # Calculate the split of the payment between interest and principal
#         principal_payment = min(remaining_principal, self.amount)
#         interest_payment = self.amount - principal_payment

#         # If the payment is greater than the remaining interest, adjust the payments
#         if interest_payment > remaining_interest:
#             interest_payment = remaining_interest
#             principal_payment = self.amount - interest_payment

#         # If principal payment exceeds remaining principal, adjust it
#         if principal_payment > remaining_principal:
#             principal_payment = remaining_principal

#         # Optionally raise an error if the amounts don't match after adjustment
#         if principal_payment + interest_payment != self.amount:
#             raise ValidationError(
#                 f"Repayment amount cannot be split correctly between principal and interest."
#             )

#         # Continue with further checks if necessary

#     def save(self, *args, **kwargs):
#         self.full_clean()  # Validate before saving
#         super().save(*args, **kwargs)
#         self.create_repayment_transaction_entries()
#         self.update_loan_balance_and_status()

#     def create_repayment_transaction_entries(self):
#         """Create debit and credit entries for the loan repayment."""
#         try:
#             TransactionHistory.objects.bulk_create(
#                 [
#                     # Debit the payment account
#                     TransactionHistory(
#                         loan=self.loan,
#                         transaction_date=self.repayment_date,
#                         amount=self.amount,
#                         transaction_type="debit",
#                         account=self.account,
#                         description=self.description,
#                     ),
#                     # Credit the loan account
#                     TransactionHistory(
#                         loan=self.loan,
#                         transaction_date=self.repayment_date,
#                         amount=self.amount,
#                         transaction_type="credit",
#                         account=self.loan.account,
#                         description=self.description,
#                     ),
#                 ]
#             )
#         except Exception as e:
#             raise ValidationError(f"Error creating transaction entries: {e}")

#     def update_loan_balance_and_status(self):
#         """Update the loan's remaining balance and status after repayment."""
#         # Ensure remaining principal and interest are not None
#         remaining_principal = self.loan.remaining_principal or Decimal("0.00")
#         remaining_interest = self.loan.remaining_interest or Decimal("0.00")

#         # Calculate the interest and principal components of the repayment
#         interest_payment = self.calculate_interest_payment() or Decimal("0.00")

#         principal_payment = self.amount - interest_payment

#         # Limit principal payment to remaining principal if necessary
#         if principal_payment > remaining_principal:
#             principal_payment = remaining_principal

#         # Update loan balances
#         self.loan.remaining_principal = remaining_principal - principal_payment
#         self.loan.remaining_interest = remaining_interest - interest_payment
#         self.loan.remaining_interest = max(
#             self.loan.remaining_interest, Decimal("0.00")
#         )  # Avoid negative interest balance

#         # Update loan status if fully repaid
#         if self.loan.remaining_principal == Decimal(
#             "0.00"
#         ) and self.loan.remaining_interest == Decimal("0.00"):
#             self.loan.status = "repaid"
#         elif timezone.now().date() > self.loan.due_date:
#             self.loan.status = "overdue"

#         self.loan.save(
#             update_fields=["remaining_principal", "remaining_interest", "status"]
#         )

#     def calculate_interest_payment(self):
#         """Calculate interest payment for the current repayment amount."""
#         if self.loan.interest_method == "flat_rate":
#             total_interest = (
#                 self.loan.principal_amount
#                 * Decimal(self.loan.interest_rate)
#                 / Decimal(100)
#             )
#             return (
#                 total_interest / self.loan.loan_period_months
#             )  # Equal monthly interest
#         elif self.loan.interest_method == "reducing_rate":
#             return self.loan.calculate_interest_payment(self.loan.remaining_principal)

#     def __str__(self):
#         return f"Repayment for Loan {self.loan.id} on {self.repayment_date} - Amount: {self.amount}"


class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    repayment_date = models.DateField()
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[("Cash", "Cash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash",
    )
    amount_repaid = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    description = models.CharField(
        max_length=255, blank=True, null=True, default="Loan repayment"
    )

    def clean(self):
        if self.amount_repaid is None:
            self.amount_repaid = Decimal("0.00")

    def save(self, *args, **kwargs):
        if not self.loan.account:
            raise ValueError("Loan must have an account assigned before repayment.")

        super().save(*args, **kwargs)
        self.create_transaction_entries()
        self.update_loan_balance_and_status()

    def create_transaction_entries(self):
        """Creates transaction entries for loan repayment."""
        # Debit the payment account (Cash or Bank) for the repayment amount
        self.create_transaction(
            account=self.account,
            transaction_type="debit",
            amount=self.amount_repaid,
            description=self.description,
        )

        # Split repayment into principal and interest portions and credit the respective accounts
        principal_payment = self.calculate_principal_payment()
        interest_payment = self.amount_repaid - principal_payment

        # Credit the loan receivable account for the principal portion
        self.create_transaction(
            account=self.loan.account,
            transaction_type="credit",
            amount=principal_payment,
            description=self.description,
        )

        # Credit the interest receivable account for the interest portion, if applicable
        if interest_payment > 0:
            interest_receivable_account = self.get_interest_receivable_account()
            self.create_transaction(
                account=interest_receivable_account,
                transaction_type="credit",
                amount=interest_payment,
                description=f"Interest received for Loan {self.loan.id}",
            )

    def get_interest_receivable_account(self):
        """Retrieve or raise an error if the interest receivable account does not exist."""
        try:
            return ChartOfAccounts.objects.get(account_number="1060")
        except ChartOfAccounts.DoesNotExist:
            raise ValueError("Loan Interest Receivable account does not exist.")

    def calculate_interest_payment(self):
        """Calculate interest payment for a specific repayment based on balance and interest method."""
        # Use the remaining principal for calculating interest on reducing rate loans
        current_balance = self.loan.remaining_principal or Decimal("0.00")

        if self.loan.interest_method == "flat_rate":
            # Flat rate interest calculation
            total_interest = (
                self.loan.principal_amount
                * Decimal(self.loan.interest_rate)
                / Decimal(100)
            )
            # Distribute evenly over the loan period
            return total_interest / Decimal(self.loan.loan_period_months)

        elif self.loan.interest_method == "reducing_rate":
            # Reducing balance interest calculation
            monthly_rate = Decimal(self.loan.interest_rate) / Decimal(100) / Decimal(12)
            return current_balance * monthly_rate

        return Decimal("0.00")  # Default if no interest method is set

    def update_loan_balance_and_status(self):
        """Update the loan's remaining balance and status after repayment."""
        remaining_principal = self.loan.remaining_principal or Decimal("0.00")
        remaining_interest = self.loan.remaining_interest or Decimal("0.00")

        # Calculate interest and principal portions
        interest_payment = self.calculate_interest_payment()
        principal_payment = self.amount_repaid - interest_payment

        # Ensure we do not overpay principal
        if principal_payment > remaining_principal:
            principal_payment = remaining_principal

        # Update the loan's balances
        self.loan.remaining_principal = remaining_principal - principal_payment
        self.loan.remaining_interest = max(
            remaining_interest - interest_payment, Decimal("0.00")
        )

        # Update loan status if fully repaid
        if self.loan.remaining_principal == Decimal(
            "0.00"
        ) and self.loan.remaining_interest == Decimal("0.00"):
            self.loan.status = "repaid"
        elif timezone.now().date() > self.loan.due_date:
            self.loan.status = "overdue"

        self.loan.save(
            update_fields=["remaining_principal", "remaining_interest", "status"]
        )

    def calculate_principal_payment(self):
        """Calculates the portion of the repayment that applies to principal."""
        total_repaid = self.loan.repayments.aggregate(total=Sum("amount_repaid"))[
            "total"
        ] or Decimal("0.00")
        remaining_principal = self.loan.principal_amount - total_repaid
        return min(self.amount_repaid, remaining_principal)

    def create_transaction(self, account, transaction_type, amount, description):
        """Helper to create a transaction history entry."""
        TransactionHistory.objects.create(
            loan=self.loan,
            transaction_date=self.repayment_date,
            amount=amount,
            transaction_type=transaction_type,
            account=account,
            description=description,
        )

    def __str__(self):
        return f"Repayment {self.id} for Loan {self.loan.id}"


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
