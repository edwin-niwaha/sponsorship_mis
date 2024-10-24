from django import forms
from .models import LoanDisbursement, Loan, Product
from apps.client.models import Client
from django.utils import timezone


class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            "borrower",
            "principal_amount",
            "interest_rate",
            "start_date",
            "due_date",
            "status",
            "account",
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
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "placeholder": "Select start date",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "placeholder": "Select due date",
                }
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "account": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the borrower field with clients
        self.fields["borrower"].queryset = Client.objects.all()


class LoanDisbursementForm(forms.ModelForm):
    class Meta:
        model = LoanDisbursement
        fields = ["disbursement_date", "amount", "account"]
        widgets = {
            "disbursement_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
            "account": forms.Select(),
        }
