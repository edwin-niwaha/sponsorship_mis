import logging
from decimal import Decimal

from django import forms
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.timezone import now
from django.core.exceptions import ValidationError

from .models import ChartOfAccounts, Loan, LoanDisbursement, LoanPenalty, LoanRepayment

logger = logging.getLogger(__name__)

# contants
min_account_number = 1010
max_account_number = 1020


# Import form
class ImportLoansForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"


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
        exclude = (
            "borrower",
            "account",
            "disbursement_date",
            "due_date",
            "status",
            "interest_method",
            "total_interest",
            "approved_by_boo",
            "approved_by_hof",
            "approved_by_ed",
            "approved_date",
            "reason_for_rejection",
            "applied_by",
            "applied_by_role",
            "created_by",
            "created_at",
        )
        widgets = {
            # "borrower": forms.Select(attrs={"class": "form-control"}),
            "principal_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter the principal amount",
                    "min": 0,
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
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
            "loan_period_months": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter loan period in months",
                    "min": 1,
                }
            ),
            "reason_for_approval": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter reason for approval",
                    "rows": 2,
                }
            ),
        }

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["borrower"].queryset = Client.objects.all()

    def save(self, commit=True, user=None):
        loan = super().save(commit=False)
        if user:
            loan.created_by = (
                user  # Set the created_by field to the user who is creating the loan
            )
        if commit:
            loan.save()
        return loan


# =================================== LoanApplicationUpdateForm ===================================
class LoanApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            "borrower",
            "principal_amount",
            "interest_rate",
            "interest_method",
            "start_date",
            "loan_period_months",
            "reason_for_approval",
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
            "reason_for_approval": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter reason for approval",
                    "rows": 3,
                }
            ),
        }

    def save(self, commit=True, user=None):
        """
        Save the form, and if a user is provided, associate them with the created loan.
        """
        loan = super().save(commit=False)
        if user:
            loan.created_by = user
        if commit:
            loan.save()
        return loan


class LoanRejectionForm(forms.Form):
    reason_for_rejection = forms.CharField(
        max_length=100,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Enter reason for rejection",
                "rows": 3,
            }
        ),
        label="Reason for Rejection",
    )


# =================================== LoanDisbursementForm ===================================
class LoanDisbursementForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(status="approved"),
        required=True,
        label="Select Loan",
        widget=forms.Select(attrs={"class": "chzn-select"}),
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
    disbursement_date = forms.DateField(
        label="Disbursement Date",
        required=True,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        initial=now().date(),  # Default to today's date
    )

    class Meta:
        model = LoanDisbursement
        fields = [
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
            pass  # Access the principal amount
            # Additional validation logic can go here if necessary

        return cleaned_data


# =================================== LoanAllDisbursementForm ===================================
class LoanAllDisbursementForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(min_account_number, max_account_number),
        ),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = LoanDisbursement
        fields = ["account", "payment_method"]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Basic validation to ensure account and payment_method are valid
        if not cleaned_data.get("account"):
            raise forms.ValidationError("A paying account must be selected.")
        if not cleaned_data.get("payment_method"):
            raise forms.ValidationError("A payment method must be selected.")
        return cleaned_data

    def save(self, approved_loans):
        """
        Custom save method to handle disbursement of all eligible loans at once
        """
        disbursed_count = 0

        for loan in approved_loans:
            # Verify disbursement_date is set
            if not loan.disbursement_date:
                raise ValidationError(
                    f"Loan {loan.id} does not have a disbursement date set."
                )

            # Create a new LoanDisbursement instance
            disbursement = LoanDisbursement(
                loan=loan,
                account=self.cleaned_data["account"],
                payment_method=self.cleaned_data["payment_method"],
            )
            disbursement.save()  # This triggers create_transaction_entries
            disbursed_count += 1

            # Update loan status to "disbursed"
            loan.status = "disbursed"
            loan.disbursement_date = loan.start_date
            loan.save()

        return disbursed_count


# =================================== LoanRepaymentForm ===================================
class LoanRepaymentForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.none(),
        label="Loan",
        widget=forms.Select(attrs={"class": "chzn-select"}),
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
    penalty_payment = forms.DecimalField(
        label="Penalty Payment",
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
            "penalty_payment",
            "account",
        ]
        widgets = {
            "repayment_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["loan"].queryset = Loan.objects.annotate(
            principal_paid=Coalesce(
                Sum("repayments__principal_payment"),
                Value(0, output_field=DecimalField()),
            ),
            interest_paid=Coalesce(
                Sum("repayments__interest_payment"),
                Value(0, output_field=DecimalField()),
            ),
            penalty_paid=Coalesce(
                Sum("repayments__penalty_payment"),
                Value(0, output_field=DecimalField()),
            ),
            remaining_principal=F("principal_amount")
            - Coalesce(
                Sum("repayments__principal_payment"),
                Value(0, output_field=DecimalField()),
            ),
            remaining_interest=F("total_interest")
            - Coalesce(
                Sum("repayments__interest_payment"),
                Value(0, output_field=DecimalField()),
            ),
            remaining_penalty=Coalesce(
                Sum(
                    "penalties__penalty_amount",
                    filter=Q(penalties__is_paid=False),
                    distinct=True,  # ✅ stops duplicates
                ),
                Value(0, output_field=DecimalField()),
            ),
        ).filter(
            Q(remaining_principal__gt=0)
            | Q(remaining_interest__gt=0)
            | Q(remaining_penalty__gt=0),
            status="disbursed",
        )

    def clean(self):
        cleaned_data = super().clean()
        principal_payment = cleaned_data.get("principal_payment") or Decimal("0.00")
        interest_payment = cleaned_data.get("interest_payment") or Decimal("0.00")
        penalty_payment = cleaned_data.get("penalty_payment") or Decimal("0.00")
        loan = cleaned_data.get("loan")

        if not loan:
            raise forms.ValidationError("Please select a loan.")

        # Get remaining balances from Loan model
        balances = loan.calculate_remaining_balances()
        remaining_principal = balances["principal_balance"]
        remaining_interest = balances["interest_balance"]
        remaining_penalty = balances["penalty_balance"]

        # Validate principal payment
        if principal_payment > remaining_principal:
            self.add_error(
                "principal_payment",
                f"Principal payment of {principal_payment:,.2f} cannot exceed the remaining principal balance of {remaining_principal:,.2f}.",
            )

        # Validate interest payment
        if interest_payment > remaining_interest:
            self.add_error(
                "interest_payment",
                f"Interest payment of {interest_payment:,.2f} cannot exceed the remaining interest balance of {remaining_interest:,.2f}.",
            )

        # Validate penalty payment: must exactly equal remaining penalty if there is one
        if remaining_penalty > 0 and penalty_payment != remaining_penalty:
            self.add_error(
                "penalty_payment",
                f"Penalty payment must equal the remaining penalty of {remaining_penalty:,.2f}.",
            )

        return cleaned_data


# =================================== LoanPenaltyForm ===================================


class LoanPenaltyForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.none(),
        label="Loan",
        widget=forms.Select(attrs={"class": "chzn-select"}),
    )
    penalty_amount = forms.DecimalField(
        label="Penalty Amount",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=0.01,
        decimal_places=2,
        max_digits=15,
        initial=0,
    )
    penalty_date = forms.DateField(
        label="Penalty Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        initial=timezone.now().date,
    )
    reason = forms.CharField(
        label="Penalty Reason",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        max_length=255,
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(account_number="1071"),
        label="Penalty Account",
        widget=forms.Select(attrs={"class": "form-control"}),
        initial=lambda: ChartOfAccounts.objects.get(account_number="1071"),
    )

    class Meta:
        model = LoanPenalty
        fields = ["loan", "penalty_date", "penalty_amount", "reason", "account"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        try:
            self.fields["loan"].queryset = (
                Loan.objects.annotate(
                    principal_paid=Coalesce(
                        Sum("repayments__principal_payment"),
                        Value(0, output_field=forms.DecimalField()),
                    ),
                    interest_paid=Coalesce(
                        Sum("repayments__interest_payment"),
                        Value(0, output_field=forms.DecimalField()),
                    ),
                    penalty_paid=Coalesce(
                        Sum("repayments__penalty_payment"),
                        Value(0, output_field=forms.DecimalField()),
                    ),
                    remaining_principal=F("principal_amount")
                    - Coalesce(
                        Sum("repayments__principal_payment"),
                        Value(0, output_field=forms.DecimalField()),
                    ),
                    remaining_interest=F("total_interest")
                    - Coalesce(
                        Sum("repayments__interest_payment"),
                        Value(0, output_field=forms.DecimalField()),
                    ),
                    remaining_penalty=Coalesce(
                        Sum(
                            "penalties__penalty_amount",
                            filter=Q(penalties__is_paid=False),
                            distinct=True,
                        ),
                        Value(0, output_field=forms.DecimalField()),
                    ),
                )
                .filter(
                    Q(remaining_principal__gt=0)
                    | Q(remaining_interest__gt=0)
                    | Q(remaining_penalty__gt=0),
                    status__in=["disbursed", "overdue"],
                )
                .distinct()
            )

            self.fields["account"].initial = ChartOfAccounts.objects.get(
                account_number="1071"
            )
        except Exception:
            self.fields["loan"].queryset = Loan.objects.filter(
                status__in=["disbursed", "overdue"]
            ).distinct()

        if user:
            self.instance.created_by = user
