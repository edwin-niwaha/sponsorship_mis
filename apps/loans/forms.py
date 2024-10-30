from django import forms
from .models import LoanDisbursement, Loan, ChartOfAccounts, LoanRepayment
from apps.client.models import Client
from django.utils import timezone

# contants
min_account_number = 1000
max_account_number = 2000


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
            ),  # Filter by account_number range
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
        queryset=Loan.objects.filter(remaining_balance__gt=0),
        label="Select Loan",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(
                min_account_number,
                max_account_number,
            ),  # Filter by account_number range
        ),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = LoanRepayment
        fields = ["loan", "repayment_date", "amount", "account"]
        widgets = {
            "repayment_date": forms.DateInput(attrs={"type": "date"}),
        }

        def clean_amount(self):
            amount = self.cleaned_data.get("amount")
            loan = self.cleaned_data.get("loan")  # Access selected loan

            if loan is not None:
                # Get the remaining balance; if None, assume it as 0 for safety.
                remaining_balance = (
                    loan.remaining_balance if loan.remaining_balance is not None else 0
                )

                # Compare the repayment amount with the remaining balance
                if amount > remaining_balance:
                    raise forms.ValidationError(
                        "Repayment amount cannot exceed the remaining balance."
                    )
            else:
                raise forms.ValidationError("No loan selected.")

            return amount
