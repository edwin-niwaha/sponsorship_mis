from django.core.exceptions import ValidationError
from django.db import models
from apps.client.models import Client


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
    borrower = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="loans")
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=[("active", "Active"), ("closed", "Closed")]
    )
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="loans"
    )

    def __str__(self):
        return f"Loan {self.id} - {self.borrower}"


# =================================== LoanDisbursement Model ===================================
class LoanDisbursement(models.Model):
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="disbursements"
    )
    disbursement_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="disbursements"
    )

    def __str__(self):
        return f"Disbursement {self.id} for Loan {self.loan.id}"

    def save(self, *args, **kwargs):
        self.full_clean()  # Validate before saving
        super().save(*args, **kwargs)
        self.create_transaction_entries()

    def create_transaction_entries(self):
        """Create transaction history entries for both the loan account and disbursement account."""
        TransactionHistory.objects.bulk_create(
            [
                # Credit the disbursement account
                TransactionHistory(
                    loan=self.loan,
                    transaction_date=self.disbursement_date,
                    amount=self.amount,
                    transaction_type="disbursement",
                    account=self.account,
                ),
                # Debit the loan account
                TransactionHistory(
                    loan=self.loan,
                    transaction_date=self.disbursement_date,
                    amount=self.amount,
                    transaction_type="disbursement",
                    account=self.loan.account,
                ),
            ]
        )


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


# =================================== TransactionHistory Model ===================================
class TransactionHistory(models.Model):
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20,
        choices=[("disbursement", "Disbursement"), ("repayment", "Repayment")],
    )
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="transactions"
    )

    def __str__(self):
        return (
            f"Transaction {self.id} for Loan {self.loan.id} on {self.transaction_date}"
        )

    def clean(self):
        # Ensure that the amount is positive
        if self.amount <= 0:
            raise ValidationError("Transaction amount must be greater than zero.")


# =================================== LoanRepayment Model ===================================
class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    repayment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.CASCADE, related_name="repayments"
    )

    def save(self, *args, **kwargs):
        self.full_clean()  # Validate before saving
        super().save(*args, **kwargs)
        self.create_repayment_transaction_entries()

    def create_repayment_transaction_entries(self):
        """Create debit and credit entries for the loan repayment."""
        TransactionHistory.objects.bulk_create(
            [
                # Debit the payment account
                TransactionHistory(
                    loan=self.loan,
                    transaction_date=self.repayment_date,
                    amount=self.amount,
                    transaction_type="repayment",
                    account=self.account,
                ),
                # Credit the loan account
                TransactionHistory(
                    loan=self.loan,
                    transaction_date=self.repayment_date,
                    amount=self.amount,
                    transaction_type="repayment",
                    account=self.loan.account,
                ),
            ]
        )
