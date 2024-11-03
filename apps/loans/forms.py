from django import forms
from django.db.models import F, Q
from .models import LoanDisbursement, Loan, ChartOfAccounts, LoanRepayment
from apps.client.models import Client
from django.utils import timezone
from decimal import Decimal, ROUND_DOWN

# contants
min_account_number = 1010
max_account_number = 1020


# =================================== ChartOfAccountsForm ===================================
class ChartOfAccountsForm(forms.ModelForm):
    class Meta:
        model = ChartOfAccounts
        fields = ["account_name", "account_type", "account_number", "description"]
        widgets = {
            "account_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Account Name"}
            ),
            "account_type": forms.Select(attrs={"class": "form-control"}),
            "account_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Account Number"}
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Description (optional)",
                }
            ),
        }

    def clean_account_number(self):
        account_number = self.cleaned_data.get("account_number")
        if account_number and len(account_number) < 3:
            raise forms.ValidationError(
                "Account number must be at least 3 characters long."
            )
        return account_number

    def clean_account_name(self):
        account_name = self.cleaned_data.get("account_name")
        if account_name and len(account_name) < 3:
            raise forms.ValidationError(
                "Account name must be at least 3 characters long."
            )
        return account_name


# =================================== ImportCOAForm ===================================
class ImportCOAForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"


# =================================== LoanApplicationForm ===================================
class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            "borrower",
            "principal_amount",
            "interest_rate",
            "start_date",
            "loan_period_months",
            "interest_method",
        ]
        widgets = {
            "borrower": forms.Select(attrs={"class": "form-control"}),
            "principal_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter the principal amount",
                    "min": 0,
                }
            ),
            "interest_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter interest rate (%)",
                    "min": 0,
                    "step": 0.01,
                }
            ),
            "interest_method": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "placeholder": "Select start date",
                }
            ),
            "loan_period_months": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter loan period in months",
                    "min": 1,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["borrower"].queryset = Client.objects.all()

    def save(self, commit=True, user=None):
        loan = super().save(commit=False)
        if user:
            loan.created_by = (
                user  # Set the created_by field to the user who is creating the loan
            )
        if commit:
            loan.save()
        return loan


# =================================== LoanDisbursementForm ===================================
class LoanDisbursementForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(status="approved"),
        required=True,
        label="Select Loan",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(
                min_account_number,
                max_account_number,
            ),
        ),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = LoanDisbursement
        fields = [
            "disbursement_date",
            "account",  # Maps directly to `account` in LoanDisbursement model
            "loan",
            "payment_method",
        ]
        widgets = {
            "disbursement_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        loan = cleaned_data.get("loan")

        if loan:
            disbursed_amount = loan.principal_amount  # Access the principal amount
            # Additional validation logic can go here if necessary

        return cleaned_data


# =================================== LoanRepaymentForm ===================================
class LoanRepaymentForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(
            Q(principal_amount__gt=0)
            | Q(total_interest__gt=0)  # Adjust fields as necessary
        ),
        label="Select Loan",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(min_account_number, max_account_number),
        ),
        label="Paying Account",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    principal_payment = forms.DecimalField(
        label="Principal Payment",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=0,
        decimal_places=2,
        max_digits=15,
        initial=0,
    )

    interest_payment = forms.DecimalField(
        label="Interest Payment",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=0,
        decimal_places=2,
        max_digits=15,
        initial=0,
    )

    class Meta:
        model = LoanRepayment
        fields = [
            "loan",
            "repayment_date",
            "principal_payment",
            "interest_payment",
            "account",
        ]
        widgets = {
            "repayment_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        principal_payment = cleaned_data.get("principal_payment")
        interest_payment = cleaned_data.get("interest_payment")
        loan = cleaned_data.get("loan")

        if not loan:
            raise forms.ValidationError("Please select a loan.")

        # Calculate remaining balances using the method from the Loan model
        balances = loan.calculate_remaining_balances()
        remaining_principal = balances[
            "principal_balance"
        ]  # Adjusted to match your return structure
        remaining_interest = balances[
            "interest_balance"
        ]  # Adjusted to match your return structure

        # Validate principal payment
        if principal_payment and principal_payment > remaining_principal:
            raise forms.ValidationError(
                f"Principal payment of {principal_payment:,.2f} cannot exceed the remaining principal balance of {remaining_principal:,.2f}."
            )

        # Validate interest payment
        if interest_payment and interest_payment > remaining_interest:
            raise forms.ValidationError(
                f"Interest payment of {interest_payment:,.2f} cannot exceed the remaining interest balance of {remaining_interest:,.2f}."
            )

        # Optionally, validate that the total payment does not exceed the total balance
        total_payment = (principal_payment or 0) + (interest_payment or 0)
        total_remaining_balance = remaining_principal + remaining_interest
        if total_payment > total_remaining_balance:
            raise forms.ValidationError(
                f"Total payment of {total_payment:,.2f} cannot exceed the total remaining balance of {total_remaining_balance:,.2f}."
            )

        return cleaned_data
