import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from datetime import timedelta, date
from django.db.models import Sum
from django.utils import timezone
from django.contrib import messages
from openpyxl import load_workbook
from .forms import (
    LoanDisbursementForm,
    LoanApplicationForm,
    ChartOfAccountsForm,
    LoanRepaymentForm,
    ImportCOAForm,
)
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import (
    LoanProduct,
    Product,
    ChartOfAccounts,
    Loan,
    LoanDisbursement,
    LoanRepayment,
    TransactionHistory,
)
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

logger = logging.getLogger(__name__)


# =================================== Loan Applications View ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_applications(request):
    queryset = get_loan_queryset(request.GET.get("search"))
    loans = paginate_queryset(queryset, request.GET.get("page"))

    return render(
        request,
        "loans/loan_applications.html",
        {"loans": loans, "table_title": "Loan Applications"},
    )


def get_loan_queryset(search_query):
    queryset = Loan.objects.prefetch_related("disbursements").all().order_by("id")
    if search_query:
        queryset = queryset.filter(full_name__icontains=search_query)
    return queryset


def paginate_queryset(queryset, page_number):
    paginator = Paginator(queryset, 25)  # Show 50 records per page
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)  # Return first page if page number is not an integer
    except EmptyPage:
        return paginator.page(
            paginator.num_pages
        )  # Return last page if page number is out of range


# =================================== Loan Apply View ===================================
@login_required
@admin_or_manager_required
def loan_apply(request):
    form_title = "Apply for Loan"
    form = LoanApplicationForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            borrower = form.cleaned_data.get("borrower")

            # Check if the selected borrower has an active (running) loan balance
            running_loan = Loan.objects.filter(
                borrower=borrower, status="disbursed"
            ).exists()
            if running_loan:
                messages.warning(
                    request,
                    f"{borrower} already has a running loan balance and cannot apply for a new loan.",
                    extra_tags="bg-warning",
                )
                return redirect("loans:apply_for_loan")

            try:
                form.save()  # Save the loan application without passing the user
                messages.success(
                    request,
                    "Loan application submitted successfully!",
                    extra_tags="bg-success",
                )
                return redirect("loans:apply_for_loan")
            except ValidationError as e:
                messages.error(request, str(e), extra_tags="bg-danger")

    context = {
        "form": form,
        "form_title": form_title,
    }
    return render(request, "loans/apply_for_loan.html", context)


# =================================== view_repayment_schedule View ===================================
def repayment_schedule(request, loan_id):
    # Fetch the loan using the provided loan ID
    loan = get_object_or_404(Loan, id=loan_id)

    # Generate the repayment schedule based on the interest method (flat_rate or reducing_rate)
    repayment_schedule = loan.generate_payment_schedule()

    # Initialize values for monthly repayments
    monthly_principal_repayment = 0
    monthly_interest_repayment = 0
    monthly_payment = 0

    # Set up calculations based on interest method
    if loan.interest_method == "flat_rate":
        if repayment_schedule:
            first_payment = repayment_schedule[0]
            monthly_principal_repayment = first_payment["principal_payment"]
            monthly_interest_repayment = first_payment["interest_payment"]
            monthly_payment = first_payment["total_payment"]
    elif loan.interest_method == "reducing_rate":
        if repayment_schedule:
            first_payment = repayment_schedule[0]
            monthly_principal_repayment = first_payment["principal_payment"]
            monthly_interest_repayment = first_payment["interest_payment"]
            monthly_payment = first_payment["total_payment"]

    # Total interest and cost of loan
    total_interest = loan.total_interest
    total_cost_of_loan = loan.principal_amount + total_interest

    # Loan period in years for display (optional)
    loan_period_years = loan.loan_period_months / 12

    # Render the repayment schedule template
    context = {
        "loan": loan,
        "repayment_schedule": repayment_schedule,
        "monthly_principal_repayment": monthly_principal_repayment,
        "monthly_interest_repayment": monthly_interest_repayment,
        "monthly_payment": monthly_payment,
        "total_cost_of_loan": total_cost_of_loan,
        "total_interest": total_interest,
        "loan_period_years": loan_period_years,
        "interest_method": loan.interest_method,  # To identify the method in the template
    }
    return render(request, "loans/repayment_schedule.html", context)


# =================================== Disbursed Loans View ===================================
@login_required
@admin_or_manager_required
def disbursed_loans_view(request):
    # Fetch loans based on optional search filtering
    queryset = get_loan_queryset(request.GET.get("search"))

    # Filter for disbursed loans
    disbursed_loans = queryset.all().prefetch_related("disbursements")

    # Paginate the filtered loans
    loans = paginate_queryset(disbursed_loans, request.GET.get("page"))

    # Process each loan and its disbursements
    loans_with_disbursement_info = [
        {
            "loan_id": loan.id,
            "borrower": loan.borrower,
            "principal_amount": loan.principal_amount,
            "total_interest": loan.total_interest,
            "interest_rate": loan.interest_rate,
            "loan_period_months": loan.loan_period_months,
            "start_date": loan.start_date,
            "due_date": loan.due_date,
            "status": loan.get_status_display(),
            "disbursement_date": disbursement.disbursement_date,
            "account_number": loan.account.account_number if loan.account else None,
            "payment_method": disbursement.payment_method,
        }
        for loan in loans
        for disbursement in loan.disbursements.all()
    ]
    context = {
        "loans_with_disbursement_info": loans_with_disbursement_info,
        "loans": loans,
        "table_title": "Disbursed Loans",
    }

    return render(request, "loans/disbursed_loans_list.html", context)


# =================================== Disburse Loan View ===================================
@login_required
@admin_or_manager_required
def disburse_loan(request):
    approved_loans = Loan.objects.filter(status="approved")
    form_title = "Disburse Approved Loans"
    form = LoanDisbursementForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            disbursement = form.save(commit=False)  # Don't save yet
            loan = form.cleaned_data.get("loan")  # Get the selected loan from the form
            disbursement.loan = loan  # Associate with the selected loan
            disbursement.save()  # Save the disbursement, triggering transaction creation

            # Update loan status
            loan.status = "disbursed"
            loan.save()  # Save the updated loan status

            messages.success(
                request,
                f"Loan ID {loan.id} has been successfully disbursed.",
                extra_tags="bg-success",
            )
            return redirect("loans:disburse_loan")
        else:
            messages.error(
                request,
                "There was an error with your submission. Please check the form.",
                extra_tags="bg-danger",
            )

    return render(
        request,
        "loans/disburse_loan.html",
        {
            "approved_loans": approved_loans,
            "form_title": form_title,
            "form": form,
        },
    )


# =================================== Approve Loan View ===================================
@login_required
@admin_or_manager_required
def approve_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    loan.status = "approved"
    loan.approved_date = timezone.now()
    loan.approved_by = request.user
    loan.save()

    messages.success(
        request, f"Loan {loan.id} approved successfully.", extra_tags="bg-success"
    )
    return redirect("loans:loan_applications")


# =================================== Reject Loan View ===================================
@login_required
@admin_or_manager_required
def reject_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id, status="pending")
    loan.status = "rejected"
    loan.save()
    messages.info(request, f"Loan {loan.id} has been rejected.", extra_tags="bg-danger")
    return redirect("loans:loan_applications")


# =================================== Delete Loan View ===================================
@login_required
@admin_or_manager_required
def delete_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)

    try:
        loan.delete()
        messages.success(
            request,
            f"Loan ID {loan.id} for {loan.borrower} deleted successfully!",
            extra_tags="bg-danger",
        )
    except Exception as e:
        messages.error(
            request,
            "An error occurred during the deletion process.",
            extra_tags="bg-danger",
        )
        print(f"Error deleting loan: {e}")

    return redirect("loans:loan_applications")


# ===================================  loan_repayment_create_view ===================================
@login_required
@admin_or_manager_required
def loan_repayment_create_view(request):
    form_title = "Repay Loans"
    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.loan = form.cleaned_data["loan"]
            repayment.save()
            messages.success(
                request,
                "Loan repayment submitted successfully.",
                extra_tags="bg-success",
            )
            return redirect(
                "loans:loan_detail", loan_id=repayment.loan.id
            )  # Update with your loan detail view name
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LoanRepaymentForm()

    return render(
        request,
        "loans/loan_repayment_form.html",
        {
            "form": form,
            "form_title": form_title,
        },
    )


# ===================================  loan_detail_view  ===================================


@login_required
@admin_or_manager_required
def loan_detail_view(request, loan_id):
    # Fetch the loan instance
    loan = get_object_or_404(Loan, id=loan_id)

    # Call to calculate remaining balances
    remaining_balances = loan.calculate_remaining_balances()

    # Fetch all repayments associated with the loan
    repayments = loan.repayments.all()  # Access repayments via related_name

    # Calculate totals for principal and interest
    totals = repayments.aggregate(
        total_principal=Sum("principal_payment"), total_interest=Sum("interest_payment")
    )

    # Get borrower's full name
    borrower_name = loan.borrower.full_name

    # Set up the form title for the view
    form_title = f"Details for {borrower_name} Loan id: ({loan.id})"

    # Render the loan detail template with necessary context
    return render(
        request,
        "loans/loan_detail.html",
        {
            "loan": loan,
            "remaining_principal": remaining_balances["principal_balance"],
            "remaining_interest": remaining_balances["interest_balance"],
            "repayments": repayments,
            "borrower_name": borrower_name,
            "total_principal": totals["total_principal"] or 0,
            "total_interest": totals["total_interest"] or 0,
            "form_title": form_title,
        },
    )


# =================================== Chart of Accounts List View ===================================
@login_required
@admin_or_manager_required
def chart_of_accounts_list_view(request):
    accounts = ChartOfAccounts.objects.all()
    accounts_by_type = {}

    # Group accounts by their account type
    for account in accounts:
        account_type = account.get_account_type_display()
        accounts_by_type.setdefault(account_type, []).append(account)

    context = {
        "accounts_by_type": accounts_by_type,
        "table_title": "Chart of Accounts",
    }
    return render(request, "loans/chart_of_accounts_list.html", context)


# =================================== Add Account View ===================================
@login_required
@admin_or_manager_required
def add_chart_of_account_view(request):
    form = ChartOfAccountsForm(request.POST or None)

    if form.is_valid():
        form.save()
        messages.success(
            request, "Account added successfully!", extra_tags="bg-success"
        )
        return redirect("loans:add_chart_of_account")

    context = {
        "form": form,
        "table_title": "Add New Account",
    }
    return render(request, "loans/chart_of_account_add.html", context)


# =================================== Account Update View ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def chart_of_account_update_view(request, account_id):
    account = get_object_or_404(ChartOfAccounts, id=account_id)
    form = ChartOfAccountsForm(request.POST or None, instance=account)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            f"Account: {account.account_name} updated successfully!",
            extra_tags="bg-success",
        )
        return redirect("loans:chart_of_accounts_list")
    elif request.method == "POST":
        messages.error(
            request, "There was an error updating the account!", extra_tags="bg-danger"
        )

    context = {"form": form, "account": account, "page_title": "Update Account"}
    return render(request, "loans/chart_of_account_update.html", context)


# =================================== Account Delete View ===================================
@login_required
@admin_required
@transaction.atomic
def chart_of_account_delete_view(request, account_id):
    account = get_object_or_404(ChartOfAccounts, id=account_id)

    try:
        account.delete()
        messages.success(
            request,
            f"Account: {account.account_name} deleted successfully!",
            extra_tags="bg-success",
        )
    except Exception as e:
        messages.error(
            request,
            "An error occurred during the deletion process.",
            extra_tags="bg-danger",
        )
        print(f"Error deleting account: {e}")

    return redirect("loans:chart_of_accounts_list")


# =================================== Process and Import Excel data ===================================
@login_required
@admin_required
@transaction.atomic
def import_coa_data(request):
    if request.method == "POST":
        form = ImportCOAForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES.get("excel_file")
            if excel_file and excel_file.name.endswith(".xlsx"):
                try:
                    # Call process_and_import_data function
                    errors = process_and_import_data(excel_file)
                    if errors:
                        for error in errors:
                            messages.error(request, error, extra_tags="bg-danger")
                    else:
                        messages.success(
                            request,
                            "Data imported successfully!",
                            extra_tags="bg-success",
                        )
                except Exception as e:
                    messages.error(
                        request, f"Error importing data: {e}", extra_tags="bg-danger"
                    )
                return redirect("loans:chart_of_accounts_list")
            else:
                messages.error(
                    request, "Please upload a valid Excel file.", extra_tags="bg-danger"
                )
    else:
        form = ImportCOAForm()
    return render(
        request,
        "loans/accounts_import.html",
        {"form_name": "Import Accounts - Excel", "form": form},
    )


# Function to import Excel data
@transaction.atomic
def process_and_import_data(excel_file):
    errors = []
    try:
        wb = load_workbook(excel_file)
        sheet = wb.active

        for row_num, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            account_name = row[0].value
            account_type = row[1].value
            account_number = row[2].value
            description = row[3].value

            # Ensure account_number is treated as a string
            if account_number is None:
                errors.append(f"Missing account number on row {row_num}")
                continue

            # Convert to string, even if it's a number
            account_number = str(account_number)

            if account_name and account_type and account_number:
                try:
                    # Validate account type
                    if (
                        account_type
                        not in dict(ChartOfAccounts.ACCOUNT_TYPE_CHOICES).keys()
                    ):
                        errors.append(
                            f"Invalid account type '{account_type}' on row {row_num}"
                        )
                        continue

                    # Validate that the account number is numeric
                    if not account_number.isdigit():
                        errors.append(
                            f"Account number must be numeric on row {row_num}"
                        )
                        continue

                    # Create the account
                    ChartOfAccounts.objects.create(
                        account_name=account_name,
                        account_type=account_type,
                        account_number=account_number,
                        description=description,
                    )
                except Exception as e:
                    errors.append(f"Error on row {row_num}: {e}")
                    logger.error(f"Error on row {row_num}: {e}")
            else:
                errors.append(f"Missing required fields on row {row_num}")
    except Exception as e:
        errors.append(f"Failed to process the Excel file: {e}")
        logger.error(f"Failed to process the Excel file: {e}")

    return errors


# =================================== ledger_report ist view ===================================
def get_financial_year_dates():
    """Returns the start and end dates for the current financial year."""
    today = date.today()

    # Check if today is after July 1st (start of the financial year)
    if today.month >= 7:
        start_date = date(today.year, 7, 1)  # July 1st of the current year
        end_date = date(today.year + 1, 6, 30)  # June 30th of the next year
    else:
        start_date = date(today.year - 1, 7, 1)  # July 1st of the previous year
        end_date = date(today.year, 6, 30)  # June 30th of the current year

    return start_date, end_date


@login_required
@admin_or_manager_required
def ledger_report_view(request):
    selected_account_id = request.GET.get("account_id")  # Get selected account ID
    ledger_data = []
    accounts = ChartOfAccounts.objects.all()  # Fetch all accounts for the dropdown
    total_debits = 0
    total_credits = 0

    # Get the start and end dates for the current financial year
    financial_year_start, financial_year_end = get_financial_year_dates()

    # Use query parameters or default to the financial year range
    start_date = request.GET.get("start_date") or financial_year_start
    end_date = request.GET.get("end_date") or financial_year_end

    selected_account = None
    opening_balance = 0

    if selected_account_id:
        selected_account = get_object_or_404(ChartOfAccounts, id=selected_account_id)

        # Get transactions within the selected date range
        ledger_data = TransactionHistory.objects.filter(
            account=selected_account, transaction_date__range=[start_date, end_date]
        ).order_by("transaction_date")

        # Get opening balance by calculating the balance before the start_date
        opening_balance_queryset = TransactionHistory.objects.filter(
            account=selected_account, transaction_date__lt=start_date
        )

        # Calculate the opening balance as the sum of all prior debits and credits
        for transaction in opening_balance_queryset:
            if transaction.transaction_type == "debit":
                opening_balance += transaction.amount
            elif transaction.transaction_type == "credit":
                opening_balance -= transaction.amount

        # Calculate debits, credits, and running balance
        running_balance = opening_balance
        for transaction in ledger_data:
            if transaction.transaction_type == "debit":
                transaction.debit = transaction.amount
                transaction.credit = 0
                total_debits += transaction.amount
            elif transaction.transaction_type == "credit":
                transaction.debit = 0
                transaction.credit = transaction.amount
                total_credits += transaction.amount
            else:
                transaction.debit = 0
                transaction.credit = 0

            # Update running balance
            running_balance += transaction.debit - transaction.credit
            transaction.running_balance = running_balance

    return render(
        request,
        "loans/ledger_report.html",
        {
            "ledger_data": ledger_data,
            "accounts": accounts,
            "selected_account": selected_account,
            "selected_account_id": selected_account_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "opening_balance": opening_balance,  # Pass opening balance to template
        },
    )
