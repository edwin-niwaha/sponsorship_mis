from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import LoanDisbursementForm
from django.contrib.auth.decorators import login_required
from .forms import LoanApplicationForm
from .models import (
    LoanProduct,
    Product,
    ChartOfAccounts,
    Loan,
    LoanDisbursement,
    LoanRepayment,
)


@login_required
def loan_applications(request):
    loans = Loan.objects.filter(status="pending")

    context = {
        "loans": loans,
        "table_title": "Loan Applications",
    }
    return render(request, "loans/loan_applications.html", context)


@login_required
def loan_application_view(request):
    form_title = "Apply for Loan"

    if request.method == "POST":
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Loan application submitted successfully!")
            return redirect(
                "loans:loan-applications"
            )  # Redirect to a success page or another view
    else:
        form = LoanApplicationForm()

    context = {
        "form": form,
        "form_title": form_title,
    }

    return render(request, "loans/apply_for_loan.html", context)


@login_required
def disbursed_loans_view(request):
    # Fetch all loans that have at least one disbursement
    disbursed_loans = Loan.objects.filter(disbursements__isnull=False).distinct()

    context = {
        "loans:disbursed-loans": disbursed_loans,
        "table_title": "Disbursed Loans",
    }

    return render(request, "loans/disbursed_loans_list.html", context)


# Loan Disbursement View
@login_required
def loan_disbursement_view(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == "POST":
        form = LoanDisbursementForm(request.POST)
        if form.is_valid():
            disbursement = form.save(commit=False)
            disbursement.loan = loan
            disbursement.save()  # This will trigger the double-entry logic
            messages.success(request, "Loan disbursement successful.")
            return redirect("loans:loan-disbursement", loan_id=loan.id)
    else:
        form = LoanDisbursementForm()

    return render(
        request, "loans/loan_disbursement_form.html", {"form": form, "loan": loan}
    )
