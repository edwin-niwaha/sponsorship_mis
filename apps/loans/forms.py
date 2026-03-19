import logging
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import ChartOfAccounts, Loan, LoanDisbursement, LoanPenalty, LoanRepayment

logger = logging.getLogger(__name__)

# Account number range for cash/bank accounts used in disbursements and repayments
MIN_ACCOUNT_NUMBER = 1010
MAX_ACCOUNT_NUMBER = 1020


# ─────────────────────────────────────────────────────────────────────────────
# Import forms
# ─────────────────────────────────────────────────────────────────────────────

class ImportLoansForm(forms.Form):
    excel_file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control-file"})
    )


class ImportCOAForm(forms.Form):
    excel_file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control-file"})
    )


# ─────────────────────────────────────────────────────────────────────────────
# ChartOfAccountsForm
# ─────────────────────────────────────────────────────────────────────────────

class ChartOfAccountsForm(forms.ModelForm):
    class Meta:
        model  = ChartOfAccounts
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
                attrs={"class": "form-control", "placeholder": "Description (optional)"}
            ),
        }

    def clean_account_number(self):
        value = self.cleaned_data.get("account_number", "")
        if len(value) < 3:
            raise forms.ValidationError("Account number must be at least 3 characters.")
        return value

    def clean_account_name(self):
        value = self.cleaned_data.get("account_name", "")
        if len(value) < 3:
            raise forms.ValidationError("Account name must be at least 3 characters.")
        return value


# ─────────────────────────────────────────────────────────────────────────────
# LoanApplicationForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanApplicationForm(forms.ModelForm):
    """
    Used for new loan applications.  Fields managed by the system
    (borrower, account, dates, status, totals, approval chain) are excluded.
    """
    class Meta:
        model  = Loan
        # Exclude all system-managed and approval-chain fields.
        # last_reminder_sent is also excluded — it is set by the notification command.
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
            "updated_at",
            "last_reminder_sent",
        )
        widgets = {
            "principal_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter the principal amount",
                    "min": 0,
                }
            ),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
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

    def save(self, commit=True, user=None):
        loan = super().save(commit=False)
        if user:
            loan.created_by = user
        if commit:
            loan.save()
        return loan


# ─────────────────────────────────────────────────────────────────────────────
# LoanApplicationUpdateForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanApplicationUpdateForm(forms.ModelForm):
    """Used to edit an existing loan application (e.g. correct a mistake)."""
    class Meta:
        model  = Loan
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
                attrs={"class": "form-control", "placeholder": "Principal amount", "min": 0}
            ),
            "interest_rate": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Interest rate (%)", "min": 0, "step": 0.01}
            ),
            "interest_method": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "loan_period_months": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Loan period (months)", "min": 1}
            ),
            "reason_for_approval": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Reason for approval", "rows": 3}
            ),
        }

    def save(self, commit=True, user=None):
        loan = super().save(commit=False)
        if user:
            loan.created_by = user
        if commit:
            loan.save()
        return loan


# ─────────────────────────────────────────────────────────────────────────────
# LoanRejectionForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanRejectionForm(forms.Form):
    reason_for_rejection = forms.CharField(
        max_length=255,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Enter reason for rejection",
                "rows": 3,
            }
        ),
        label="Reason for Rejection",
    )


# ─────────────────────────────────────────────────────────────────────────────
# LoanDisbursementForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanDisbursementForm(forms.ModelForm):
    """Single-loan disbursement form."""

    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(status="approved"),
        required=True,
        label="Select Loan",
        widget=forms.Select(attrs={"class": "chzn-select"}),
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(MIN_ACCOUNT_NUMBER, MAX_ACCOUNT_NUMBER),
        ),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    disbursement_date = forms.DateField(
        label="Disbursement Date",
        required=True,
        initial=timezone.now().date,   # callable — evaluated fresh each render
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model  = LoanDisbursement
        fields = ["loan", "account", "payment_method"]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        loan = cleaned_data.get("loan")
        disbursement_date = cleaned_data.get("disbursement_date")

        if loan and disbursement_date:
            # Disbursement date must not be before the loan application date
            if disbursement_date < loan.start_date:
                raise forms.ValidationError(
                    f"Disbursement date cannot be before the loan application date "
                    f"({loan.start_date})."
                )
        return cleaned_data


# ─────────────────────────────────────────────────────────────────────────────
# LoanAllDisbursementForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanAllDisbursementForm(forms.ModelForm):
    """Bulk disbursement form — disburses all eligible approved loans at once."""

    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(MIN_ACCOUNT_NUMBER, MAX_ACCOUNT_NUMBER),
        ),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model  = LoanDisbursement
        fields = ["account", "payment_method"]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("account"):
            raise forms.ValidationError("A paying account must be selected.")
        if not cleaned_data.get("payment_method"):
            raise forms.ValidationError("A payment method must be selected.")
        return cleaned_data

    def save(self, approved_loans):
        """
        Disburse all eligible loans.
        Sets disbursement_date to today if not already set.
        Calls disbursement.save() which triggers _post_entries() in the model.
        """
        disbursed_count = 0
        today = timezone.now().date()

        for loan in approved_loans:
            # Set disbursement_date if missing — use today
            if not loan.disbursement_date:
                loan.disbursement_date = today

            loan.status = "disbursed"
            loan.save()   # calculate_due_date() + calculate_interest() run here

            LoanDisbursement.objects.create(
                loan=loan,
                account=self.cleaned_data["account"],
                payment_method=self.cleaned_data["payment_method"],
            )   # model save() triggers _post_entries()

            disbursed_count += 1

        return disbursed_count


# ─────────────────────────────────────────────────────────────────────────────
# Shared queryset helper for loan dropdowns
# ─────────────────────────────────────────────────────────────────────────────

def _active_loans_with_balance():
    """
    Returns loans with status disbursed/overdue that still have an
    outstanding balance, annotated for dropdown display.

    Uses DB-level annotation so the queryset is a single query.
    The penalty annotation uses distinct=True to prevent fan-out
    when a loan has both repayments and penalties.
    """
    return (
        Loan.objects.annotate(
            remaining_principal=F("principal_amount") - Coalesce(
                Sum("repayments__principal_payment"),
                Value(0, output_field=DecimalField()),
            ),
            remaining_interest=F("total_interest") - Coalesce(
                Sum("repayments__interest_payment"),
                Value(0, output_field=DecimalField()),
            ),
            # distinct=True prevents duplicate rows from the penalties join
            remaining_penalty=Coalesce(
                Sum(
                    "penalties__penalty_amount",
                    filter=Q(penalties__is_paid=False),
                    distinct=True,
                ),
                Value(0, output_field=DecimalField()),
            ),
        )
        .filter(
            Q(remaining_principal__gt=0)
            | Q(remaining_interest__gt=0)
            | Q(remaining_penalty__gt=0),
            status__in=["disbursed", "overdue"],
        )
        .distinct()
        .select_related("borrower")
    )


# ─────────────────────────────────────────────────────────────────────────────
# LoanRepaymentForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanRepaymentForm(forms.ModelForm):
    """
    Changes vs original:
    • Loan queryset uses shared _active_loans_with_balance() helper.
    • clean() validates against calculate_remaining_balances() (model method)
      which is the single source of truth — consistent with LoanRepayment.clean().
    • Removed the "penalty must exactly equal remaining" rule — partial penalty
      payments are valid (model supports them via _mark_penalties_paid).
    • Added zero-payment guard: at least one payment field must be > 0.
    """

    loan = forms.ModelChoiceField(
        queryset=Loan.objects.none(),   # populated in __init__
        label="Loan",
        widget=forms.Select(attrs={"class": "chzn-select"}),
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            account_number__range=(MIN_ACCOUNT_NUMBER, MAX_ACCOUNT_NUMBER),
        ),
        label="Paying Account",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    principal_payment = forms.DecimalField(
        label="Principal Payment",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=Decimal("0"),
        decimal_places=2,
        max_digits=15,
        initial=Decimal("0.00"),
        required=False,
    )
    interest_payment = forms.DecimalField(
        label="Interest Payment",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=Decimal("0"),
        decimal_places=2,
        max_digits=15,
        initial=Decimal("0.00"),
        required=False,
    )
    penalty_payment = forms.DecimalField(
        label="Penalty Payment",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=Decimal("0"),
        decimal_places=2,
        max_digits=15,
        initial=Decimal("0.00"),
        required=False,
    )

    class Meta:
        model  = LoanRepayment
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
        self.fields["loan"].queryset = _active_loans_with_balance()

    def clean(self):
        cleaned_data       = super().clean()
        loan               = cleaned_data.get("loan")
        principal_payment  = cleaned_data.get("principal_payment")  or Decimal("0.00")
        interest_payment   = cleaned_data.get("interest_payment")   or Decimal("0.00")
        penalty_payment    = cleaned_data.get("penalty_payment")    or Decimal("0.00")

        if not loan:
            raise forms.ValidationError("Please select a loan.")

        # Guard: at least one field must be non-zero
        if principal_payment + interest_payment + penalty_payment <= 0:
            raise forms.ValidationError(
                "At least one payment field (principal, interest, or penalty) must be greater than zero."
            )

        # Use model method — single source of truth, consistent with LoanRepayment.clean()
        balances = loan.calculate_remaining_balances()

        if principal_payment > balances["principal_balance"]:
            self.add_error(
                "principal_payment",
                f"Cannot exceed remaining principal balance of "
                f"{balances['principal_balance']:,.2f}.",
            )
        if interest_payment > balances["interest_balance"]:
            self.add_error(
                "interest_payment",
                f"Cannot exceed remaining interest balance of "
                f"{balances['interest_balance']:,.2f}.",
            )
        if penalty_payment > balances["penalty_balance"]:
            self.add_error(
                "penalty_payment",
                f"Cannot exceed remaining penalty balance of "
                f"{balances['penalty_balance']:,.2f}.",
            )

        return cleaned_data


# ─────────────────────────────────────────────────────────────────────────────
# LoanPenaltyForm
# ─────────────────────────────────────────────────────────────────────────────

class LoanPenaltyForm(forms.ModelForm):
    """
    Changes vs original:
    • Loan queryset uses shared _active_loans_with_balance() helper.
    • account queryset uses get_or_none pattern with a clear fallback message
      instead of silently falling back to all disbursed/overdue loans.
    • output_field in annotations uses DecimalField() from django.db.models
      (not forms.DecimalField) — fixes the original type mismatch.
    """

    loan = forms.ModelChoiceField(
        queryset=Loan.objects.none(),   # populated in __init__
        label="Loan",
        widget=forms.Select(attrs={"class": "chzn-select"}),
    )
    penalty_amount = forms.DecimalField(
        label="Penalty Amount",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        min_value=Decimal("0.01"),
        decimal_places=2,
        max_digits=15,
    )
    penalty_date = forms.DateField(
        label="Penalty Date",
        initial=timezone.now().date,   # callable — evaluated fresh each render
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    reason = forms.CharField(
        label="Penalty Reason",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(account_number="1071"),
        label="Penalty Account",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model  = LoanPenalty
        fields = ["loan", "penalty_date", "penalty_amount", "reason", "account"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Loan dropdown — loans with outstanding balances
        self.fields["loan"].queryset = _active_loans_with_balance()

        # Pre-select the penalty receivable account (1071) if it exists
        try:
            self.fields["account"].initial = ChartOfAccounts.objects.get(
                account_number="1071"
            )
        except ChartOfAccounts.DoesNotExist:
            logger.warning(
                "Penalty account 1071 not found — "
                "please create it in Chart of Accounts."
            )

        if user:
            self.instance.created_by = user

    def clean_penalty_amount(self):
        amount = self.cleaned_data.get("penalty_amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Penalty amount must be positive.")
        return amount

    def clean_penalty_date(self):
        penalty_date = self.cleaned_data.get("penalty_date")
        if penalty_date and penalty_date > timezone.now().date():
            raise forms.ValidationError("Penalty date cannot be in the future.")
        return penalty_date
