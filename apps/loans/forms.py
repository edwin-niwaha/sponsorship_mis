from django import forms
from .models import LoanDisbursement, Loan, Product, ChartOfAccounts
from apps.client.models import Client
from django.utils import timezone


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
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
        label="Select Loan",
    )
    paying_account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(account_type="asset"),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = LoanDisbursement
        fields = [
            "disbursement_date",
            "amount",
            "paying_account",
            "loan",
            "payment_method",
        ]
        widgets = {
            "disbursement_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "amount": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control"}
            ),
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount <= 0:
            raise forms.ValidationError(
                "The disbursement amount must be greater than zero."
            )
        return amount
