import logging
from datetime import date, datetime
from decimal import Decimal

import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import load_workbook

logger = logging.getLogger(__name__)
from apps.client.models import Client
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

from .forms import (
    ChartOfAccountsForm,
    ImportCOAForm,
    ImportLoansForm,
    LoanAllDisbursementForm,
    LoanApplicationForm,
    LoanDisbursementForm,
    LoanPenaltyForm,
    LoanRepaymentForm,
)
from .models import (
    ChartOfAccounts,
    Loan,
    LoanRepayment,
    TransactionHistory,
)

logger = logging.getLogger(__name__)


# =================================== Loan Applications View ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_applications_view(request):
    user = request.user
    search_query = request.GET.get("search", "")
    page = request.GET.get("page", 1)
    per_page = 50  # Number of items per page

    # Get filtered loan applications
    queryset = get_loan_queryset(search_query).filter(
        status__in=["pending", "boo_approved", "hof_approved"]
    )

    # Apply role-based filtering
    if user.profile.role in ["staff", "guest"]:
        queryset = queryset.filter(applied_by=user)

    # Set up pagination
    paginator = Paginator(queryset, per_page)
    try:
        loans = paginator.page(page)
    except PageNotAnInteger:
        loans = paginator.page(1)
    except EmptyPage:
        loans = paginator.page(paginator.num_pages)

    context = {
        "loans": loans,
        "table_title": "Loan Applications",
        "search_query": search_query,
        "page_obj": loans,  # For pagination template access
    }

    return render(request, "loans/loan_applications.html", context)


# =================================== All Loan Applications View ===================================


@login_required
@admin_or_manager_or_staff_required
def loan_applications_all_view(request):
    user = request.user
    search_query = request.GET.get("search", "")
    page = request.GET.get("page", 1)
    per_page = 100
    sort_by = request.GET.get("sort", "id")  # default sort
    show_bad = request.GET.get("bad", "false")  # toggle bad loans

    # Get filtered loan applications
    queryset = get_loan_queryset(search_query)

    # Apply role-based filtering
    if user.profile.role in ["staff", "guest"]:
        queryset = queryset.filter(applied_by=user)

    # Show only bad loans if ?bad=true
    if show_bad.lower() == "true":
        queryset = queryset.filter(
            Q(borrower_id__isnull=True)
            | ~Q(
                borrower_id__in=queryset.model._meta.get_field(
                    "borrower"
                ).related_model.objects.values_list("id", flat=True)
            )
        )

    # Apply sorting
    if sort_by in ["id", "-id", "borrower_id", "-borrower_id"]:
        queryset = queryset.order_by(sort_by)

    # Set up pagination
    paginator = Paginator(queryset, per_page)
    try:
        loans = paginator.page(page)
    except PageNotAnInteger:
        loans = paginator.page(1)
    except EmptyPage:
        loans = paginator.page(paginator.num_pages)

    context = {
        "loans": loans,
        "table_title": (
            "All Loan Applications" if show_bad != "true" else "Bad Loan Applications"
        ),
        "search_query": search_query,
        "page_obj": loans,
        "current_sort": sort_by,
        "show_bad": show_bad,
    }

    return render(request, "loans/loan_applications_all.html", context)


# ===========================================
def get_loan_queryset(search_query):
    queryset = Loan.objects.prefetch_related("disbursements").all().order_by("id")
    if search_query:
        queryset = queryset.filter(borrower__full_name__icontains=search_query)
    return queryset


def paginate_queryset(queryset, page_number):
    paginator = Paginator(queryset, 50)
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)  # Return first page if page number is not an integer
    except EmptyPage:
        return paginator.page(
            paginator.num_pages
        )  # Return last page if page number is out of range


# =================================== Loan Apply View ===================================


# def send_loan_application_email(
#     recipient_name, client_name, recipient_email, application_id, is_applicant=True
# ):
#     """
#     Sends an email notification for loan application status or request for officer approval.

#     Args:
#         recipient_name (str): Name of the recipient.
#         recipient_email (str): Email address of the recipient.
#         application_id (str): Unique ID of the loan application.
#         is_applicant (bool): True if the email is for the applicant, False for the officer.

#     Returns:
#         bool: True if the email was sent successfully, False otherwise.
#     """
#     applicant_dashboard_url = "https://sponsorwithpendeza.org/loans/applications/"
#     officer_review_url = "https://sponsorwithpendeza.org/loans/applications/"
#     subject = (
#         "Your Loan Application Submitted"
#         if is_applicant
#         else "New Loan Application for Review"
#     )

#     if is_applicant:
#         email_body = f"""
#         <html>
#         <body style="font-family: Arial, sans-serif; color: #333;">
#             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
#                 <h2 style="color: #2E86C1; text-align: center;">Loan Application Submitted on Behalf of Client</h2>
#                 <p>Hello <strong>{recipient_name}</strong>,</p>
#                 <p>A loan application has been successfully submitted on behalf of <strong>{client_name}</strong>. The application ID is <strong>{application_id}</strong>. You can track the status of this application by clicking the button below:</p>
#                 <div style="text-align: center; margin: 20px 0;">
#                     <a href="{applicant_dashboard_url}" style="background-color: #2E86C1; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Application Status</a>
#                 </div>
#                 <p>Thank you for assisting clients with their financial needs through Pendeza Uganda.</p>
#                 <p style="color: #888;">- Pendeza Uganda - Finance Department</p>
#             </div>
#         </body>
#         </html>
#         """

#     else:
#         email_body = f"""
#         <html>
#         <body style="font-family: Arial, sans-serif; color: #333;">
#             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
#                 <h2 style="color: #C0392B; text-align: center;">Loan Application Approval Needed</h2>
#                 <p>Hello <strong>{recipient_name}</strong>,</p>
#                 <p>A new loan application with ID <strong>{application_id}</strong> is awaiting your review. Please review and process the application by clicking the button below:</p>
#                 <div style="text-align: center; margin: 20px 0;">
#                     <a href="{officer_review_url}" style="background-color: #C0392B; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">Review Application</a>
#                 </div>
#                 <p>Thank you for your prompt attention to this matter.</p>
#                 <p style="color: #888;">- Pendeza Uganda - Finance Department</p>
#             </div>
#         </body>
#         </html>
#         """

#     from_email = getattr(settings, "EMAIL_HOST_USER", None)
#     to = [recipient_email]

#     try:
#         email = EmailMultiAlternatives(subject, strip_tags(email_body), from_email, to)
#         email.attach_alternative(email_body, "text/html")
#         email.send()
#         return True
#     except Exception as e:
#         logger.error(f"Error sending email to {recipient_email}: {str(e)}")
#         return False

# @login_required
# def loan_apply(request):
#     form_title = "Loan Application Form"
#     form = LoanApplicationForm(request.POST or None)
#     borrowers = Client.objects.all().order_by("id")

#     logged_in_user = request.user
#     user_role = getattr(logged_in_user.profile, "role", "guest")

#     if request.method == "POST":
#         if form.is_valid():
#             borrower_id = request.POST.get("id")
#             borrower = get_object_or_404(Client, pk=borrower_id)

#             # Check if the borrower has any running loans with a non-zero balance
#             running_loans = Loan.objects.filter(
#                 borrower=borrower, status__in=["disbursed", "overdue"]
#             )

#             has_running_balance = False
#             for loan in running_loans:
#                 balances = loan.calculate_remaining_balances()
#                 total_balance = (
#                     balances["principal_balance"]
#                     + balances["interest_balance"]
#                     + balances["penalty_balance"]
#                 )
#                 if total_balance > Decimal("0.00"):
#                     has_running_balance = True
#                     break

#             if has_running_balance:
#                 error_message = (
#                     f"{borrower} has an existing loan with an outstanding balance. "
#                     "Please settle the outstanding amount before applying for a new loan."
#                 )
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse(
#                         {"success": False, "message": error_message}, status=400
#                     )
#                 messages.warning(request, error_message, extra_tags="bg-warning")
#                 return redirect("loans:apply_for_loan")

#             try:
#                 # Save the loan application
#                 application = form.save(commit=False)
#                 application.borrower = borrower
#                 application.disbursement_date = timezone.now()
#                 application.applied_by = logged_in_user
#                 application.applied_by_role = user_role
#                 application.save()

#                 # Extract client (borrower) name
#                 client_name = (
#                     borrower.get_full_name()
#                     if hasattr(borrower, "get_full_name")
#                     else str(borrower)
#                 )

#                 # Send email to logged-in user
#                 send_loan_application_email(
#                     recipient_name=logged_in_user.username,
#                     recipient_email=logged_in_user.email,
#                     application_id=application.id,
#                     client_name=client_name,
#                     is_applicant=True,
#                 )

#                 # Send email to loan officer
#                 boo_email = settings.BOO_EMAIL
#                 send_loan_application_email(
#                     recipient_name="Loan Officer",
#                     recipient_email=boo_email,
#                     application_id=application.id,
#                     client_name=client_name,
#                     is_applicant=False,
#                 )

#                 success_message = "Loan application submitted successfully!"
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse({"success": True, "message": success_message})
#                 messages.success(request, success_message, extra_tags="bg-success")
#                 return redirect("loans:apply_for_loan")

#             except ValidationError as e:
#                 error_message = str(e)
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse(
#                         {"success": False, "message": error_message}, status=400
#                     )
#                 messages.error(request, error_message, extra_tags="bg-danger")

#     context = {
#         "form": form,
#         "form_title": form_title,
#         "borrowers": borrowers,
#     }
#     return render(request, "loans/apply_for_loan.html", context)


# @login_required
# def loan_apply(request):
#     """
#     Handles the loan application process:
#     - Validates the submitted form
#     - Checks for existing running loans with outstanding balances
#     - Creates a new loan application if valid
#     - Sends asynchronous email notifications (to applicant & loan officer)
#     """
#     form_title = "Loan Application Form"
#     form = LoanApplicationForm(request.POST or None)
#     borrowers = Client.objects.all().order_by("id")

#     logged_in_user = request.user
#     user_role = getattr(logged_in_user.profile, "role", "guest")

#     if request.method == "POST":
#         if form.is_valid():
#             borrower_id = request.POST.get("id")
#             borrower = get_object_or_404(Client, pk=borrower_id)

#             # 🔎 Step 1: Check running loans with outstanding balances
#             running_loans = Loan.objects.filter(
#                 borrower=borrower, status__in=["disbursed", "overdue"]
#             )

#             has_running_balance = False
#             for loan in running_loans:
#                 balances = loan.calculate_remaining_balances()
#                 total_balance = (
#                     balances.get("principal_balance", Decimal("0.00"))
#                     + balances.get("interest_balance", Decimal("0.00"))
#                     + balances.get("penalty_balance", Decimal("0.00"))
#                 )
#                 if total_balance > Decimal("0.00"):
#                     has_running_balance = True
#                     break

#             if has_running_balance:
#                 error_message = (
#                     f"{borrower} has an existing loan with an outstanding balance. "
#                     "Please settle the outstanding amount before applying for a new loan."
#                 )
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse(
#                         {"success": False, "message": error_message}, status=400
#                     )
#                 messages.warning(request, error_message, extra_tags="bg-warning")
#                 return redirect("loans:apply_for_loan")

#             try:
#                 # 💾 Step 2: Save new loan application
#                 application = form.save(commit=False)
#                 application.borrower = borrower
#                 application.disbursement_date = timezone.now()
#                 application.applied_by = logged_in_user
#                 application.applied_by_role = user_role
#                 application.save()

#                 client_name = (
#                     borrower.get_full_name()
#                     if hasattr(borrower, "get_full_name")
#                     else str(borrower)
#                 )

#                 # 📧 Step 3: Queue emails asynchronously
#                 send_loan_application_email_task.delay(
#                     recipient_name=logged_in_user.username,
#                     recipient_email=logged_in_user.email,
#                     application_id=application.id,
#                     client_name=client_name,
#                     is_applicant=True,
#                 )

#                 boo_email = settings.BOO_EMAIL
#                 send_loan_application_email_task.delay(
#                     recipient_name="Loan Officer",
#                     recipient_email=boo_email,
#                     application_id=application.id,
#                     client_name=client_name,
#                     is_applicant=False,
#                 )

#                 # ✅ Step 4: Respond success
#                 success_message = "Loan application submitted successfully!"
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse({"success": True, "message": success_message})
#                 messages.success(request, success_message, extra_tags="bg-success")
#                 return redirect("loans:apply_for_loan")

#             except ValidationError as e:
#                 error_message = str(e)
#                 logger.error(
#                     f"Validation error while applying for loan: {error_message}"
#                 )
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse(
#                         {"success": False, "message": error_message}, status=400
#                     )
#                 messages.error(request, error_message, extra_tags="bg-danger")

#             except Exception as e:
#                 logger.exception(f"Unexpected error in loan_apply view: {str(e)}")
#                 error_message = "An unexpected error occurred while processing the loan application."
#                 if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                     return JsonResponse(
#                         {"success": False, "message": error_message}, status=500
#                     )
#                 messages.error(request, error_message, extra_tags="bg-danger")

#         else:
#             # 🚫 Step 5: Form invalid
#             error_message = "Please correct the errors below."
#             if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#                 return JsonResponse(
#                     {"success": False, "message": error_message}, status=400
#                 )
#             messages.error(request, error_message, extra_tags="bg-danger")

#     # 🎨 Render form page
#     context = {
#         "form": form,
#         "form_title": form_title,
#         "borrowers": borrowers,
#     }
#     return render(request, "loans/apply_for_loan.html", context)


@login_required
def loan_apply(request):
    """
    Handles the loan application process:
    - Validates the submitted form
    - Checks for existing running loans with outstanding balances
    - Creates a new loan application if valid
    """
    form_title = "Loan Application Form"
    form = LoanApplicationForm(request.POST or None)
    borrowers = Client.objects.all().order_by("id")

    logged_in_user = request.user
    user_role = getattr(logged_in_user.profile, "role", "guest")

    if request.method == "POST":
        if form.is_valid():
            borrower_id = request.POST.get("id")
            borrower = get_object_or_404(Client, pk=borrower_id)

            # 🔎 Step 1: Check running loans with outstanding balances
            running_loans = Loan.objects.filter(
                borrower=borrower, status__in=["disbursed", "overdue"]
            )

            has_running_balance = False
            for loan in running_loans:
                balances = loan.calculate_remaining_balances()
                total_balance = (
                    balances.get("principal_balance", Decimal("0.00"))
                    + balances.get("interest_balance", Decimal("0.00"))
                    + balances.get("penalty_balance", Decimal("0.00"))
                )
                if total_balance > Decimal("0.00"):
                    has_running_balance = True
                    break

            if has_running_balance:
                error_message = (
                    f"{borrower} has an existing loan with an outstanding balance. "
                    "Please settle the outstanding amount before applying for a new loan."
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": False, "message": error_message}, status=400
                    )
                messages.warning(request, error_message, extra_tags="bg-warning")
                return redirect("loans:apply_for_loan")

            try:
                # 💾 Step 2: Save new loan application
                application = form.save(commit=False)
                application.borrower = borrower
                application.disbursement_date = timezone.now()
                application.applied_by = logged_in_user
                application.applied_by_role = user_role
                application.save()

                # ✅ Step 3: Respond success
                success_message = "Loan application submitted successfully!"
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": True, "message": success_message})
                messages.success(request, success_message, extra_tags="bg-success")
                return redirect("loans:apply_for_loan")

            except ValidationError as e:
                error_message = str(e)
                logger.error(
                    f"Validation error while applying for loan: {error_message}"
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": False, "message": error_message}, status=400
                    )
                messages.error(request, error_message, extra_tags="bg-danger")

            except Exception as e:
                logger.exception(f"Unexpected error in loan_apply view: {str(e)}")
                error_message = "An unexpected error occurred while processing the loan application."
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": False, "message": error_message}, status=500
                    )
                messages.error(request, error_message, extra_tags="bg-danger")

        else:
            # 🚫 Step 4: Form invalid
            error_message = "Please correct the errors below."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": error_message}, status=400
                )
            messages.error(request, error_message, extra_tags="bg-danger")

    # 🎨 Render form page
    context = {
        "form": form,
        "form_title": form_title,
        "borrowers": borrowers,
    }
    return render(request, "loans/apply_for_loan.html", context)


# =================================== update_loan View ===================================
@admin_or_manager_required
def update_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    form_title = "Update Loan Details"

    if request.method == "POST":
        form = LoanApplicationForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Loan details updated successfully.", extra_tags="bg-success"
            )
            return redirect("loans:loan_applications")
        else:
            messages.error(
                request, "Please correct the errors below.", extra_tags="bg-danger"
            )
    else:
        form = LoanApplicationForm(instance=loan)

    return render(
        request,
        "loans/loan_update.html",
        {"form": form, "loan": loan, "form_title": form_title},
    )


# =================================== view_repayment_schedule View ===================================
@login_required
@admin_or_manager_or_staff_required
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
@admin_or_manager_or_staff_required
def disbursed_loans_view(request):
    # Fetch loans based on optional search filtering
    queryset = get_loan_queryset(request.GET.get("search"))

    # Filter for disbursed loans
    # disbursed_loans = queryset.filter(status="disbursed").prefetch_related(
    #     "disbursements"
    # )
    disbursed_loans = queryset.filter(
        status__in=["disbursed", "overdue", "repaid"]
    ).prefetch_related("disbursements")

    # Paginate the filtered loans
    loans = paginate_queryset(disbursed_loans, request.GET.get("page"))

    # Calculate the total disbursed amount
    total_disbursed = sum(loan.principal_amount for loan in disbursed_loans)
    total_interest_all = sum(loan.total_interest for loan in disbursed_loans)

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
            "disbursement_date": loan.disbursement_date,
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
        "total_disbursed": total_disbursed,
        "total_interest_all": total_interest_all,
    }

    return render(request, "loans/disbursed_loans_list.html", context)


# =================================== Approved Loans View ===================================
@login_required
@admin_or_manager_or_staff_required
def approved_loans_view(request):
    user = request.user
    search_query = request.GET.get("search")
    page = request.GET.get("page")

    # Fetch only approved loan applications based on search criteria
    queryset = get_loan_queryset(search_query).filter(status="approved")

    # Apply role-based filtering
    if user.profile.role in ["staff", "guest"]:
        queryset = queryset.filter(applied_by=user)

    # Paginate the results
    loans = paginate_queryset(queryset, page)

    context = {
        "loans": loans,
        "table_title": "Pending Loan Disbursements",
        "search_query": search_query,
    }

    return render(request, "loans/approved_loans_list.html", context)


# =================================== Rejected Loans View ===================================
@login_required
@admin_or_manager_or_staff_required
def rejected_loans_view(request):
    user = request.user
    search_query = request.GET.get("search")
    page = request.GET.get("page")

    # Fetch loan applications with the required statuses
    queryset = get_loan_queryset(search_query).filter(
        status__in=["ed_rejected", "hof_rejected"]
    )

    # Apply role-based filtering
    if user.profile.role in ["staff", "guest"]:
        queryset = queryset.filter(applied_by=user)

    # Paginate the results
    loans = paginate_queryset(queryset, page)

    context = {
        "loans": loans,
        "table_title": "Rejected Loans",
        "search_query": search_query,
    }

    return render(request, "loans/rejected_loans_list.html", context)


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

            # Get the disbursement_date from the form
            disbursement_date = form.cleaned_data.get("disbursement_date")

            # Set the disbursement_date on the related Loan model
            loan.disbursement_date = (
                disbursement_date  # Update loan's disbursement_date
            )

            loan.status = "disbursed"  # Update loan status
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


# =================================== Disburse All Loans View ===================================
@login_required
@admin_or_manager_required
def disburse_all_loans(request):
    # Get all approved loans
    approved_loans = Loan.objects.filter(
        status="approved"
    )  # Only "approved" loans, excluding "overdue"

    # Filter out loans for borrowers with running loan balances
    eligible_loans = []
    ineligible_loans = []

    for loan in approved_loans:
        # Check if the borrower has any running loans (disbursed or overdue with non-zero balance)
        running_loans = Loan.objects.filter(
            borrower=loan.borrower, status__in=["disbursed", "overdue"]
        ).exclude(
            id=loan.id
        )  # Exclude the current loan being considered

        has_running_balance = False
        for running_loan in running_loans:
            balances = running_loan.calculate_remaining_balances()
            total_balance = (
                balances["principal_balance"]
                + balances["interest_balance"]
                + balances["penalty_balance"]
            )
            if total_balance > Decimal("0.00"):
                has_running_balance = True
                break

        if not has_running_balance:
            eligible_loans.append(loan)
        else:
            ineligible_loans.append(loan)

    # If no eligible loans are available, show a warning and redirect
    if not eligible_loans:
        messages.warning(
            request,
            "No approved loans available for disbursement. Some borrowers may have existing running loan balances.",
            extra_tags="bg-warning",
        )
        return redirect("loans:disbursed_loans")

    form_title = "Disburse All Approved Loans"
    form = LoanAllDisbursementForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            # Call the custom save method and pass eligible loans
            disbursed_count = form.save(eligible_loans)

            # Show success message with the number of disbursed loans
            messages.success(
                request,
                f"{disbursed_count} loans have been successfully disbursed.",
                extra_tags="bg-success",
            )

            # If there were ineligible loans, inform the user
            if ineligible_loans:
                messages.warning(
                    request,
                    f"{len(ineligible_loans)} approved loans were not disbursed due to existing running loan balances.",
                    extra_tags="bg-warning",
                )

            return redirect("loans:disburse_all_loans")
        else:
            messages.error(
                request,
                "There was an error with your submission. Please check the form.",
                extra_tags="bg-danger",
            )

    return render(
        request,
        "loans/disburse_all_loans.html",
        {
            "form_title": form_title,
            "form": form,
        },
    )


# =================================== Approve Loan View ===================================
# @login_required
# def approve_loan(request, loan_id):
#     loan = get_object_or_404(Loan, id=loan_id)
#     current_user = request.user

#     if loan.status == "pending" and current_user.profile.role == "boo":
#         loan.status = "boo_approved"
#         loan.approved_by_boo = current_user
#         loan.save()

#         # Notify HOF with an HTML email
#         subject = f"Loan {loan.id} Approved by BOO"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
#                 <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
#                     <h2 style="color: #2c3e50; text-align: center;">Loan Approval Notification</h2>
#                     <p style="font-size: 16px; color: #34495e; line-height: 1.6;">Dear HOF,</p>
#                     <p style="font-size: 16px; color: #34495e; line-height: 1.6;">
#                         Loan <strong style="color: #e74c3c;">{loan.id}</strong> for <strong style="color: #e74c3c;">{loan.borrower.full_name}</strong>
#                         (Amount: <strong style="color: #e74c3c;">UGX {loan.principal_amount:,.2f}</strong>) has been approved by
#                         <strong style="color: #e74c3c;">{current_user.username}</strong>.
#                         Please review for HOF approval.
#                     </p>
#                     <p style="text-align: center;">
#                         <a href="{request.build_absolute_uri('/loans/applications/')}" style="background-color: #4CAF50; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block; margin-top: 20px;">
#                             Approve Loan
#                         </a>
#                     </p>
#                 </div>
#             </body>
#         </html>
#         """

#         email = EmailMessage(
#             subject=subject,
#             body=message,
#             from_email=settings.EMAIL_HOST_USER,
#             to=[settings.HOF_EMAIL],
#         )
#         email.content_subtype = "html"
#         email.send()

#         messages.success(
#             request, f"Loan {loan.id} approved by BOO.", extra_tags="bg-success"
#         )

#     elif loan.status == "boo_approved" and current_user.profile.role == "hof":
#         loan.status = "hof_approved"
#         loan.approved_by_hof = current_user
#         loan.save()

#         # Notify BOO and ED with an HTML email
#         subject = f"Loan {loan.id} Approved by HOF"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
#                 <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
#                     <h2 style="color: #2c3e50; text-align: center;">Loan Approval Notification</h2>
#                     <p style="font-size: 16px; color: #34495e; line-height: 1.6;">Dear ED,</p>
#                     <p style="font-size: 16px; color: #34495e; line-height: 1.6;">
#                         Loan <strong style="color: #e74c3c;">{loan.id}</strong> for <strong style="color: #e74c3c;">{loan.borrower.full_name}</strong>
#                         (Amount: <strong style="color: #e74c3c;">UGX {loan.principal_amount:,.2f}</strong>) has been approved by
#                         <strong style="color: #e74c3c;">{current_user.username}</strong>.
#                         Please review for ED approval.
#                     </p>
#                     <p style="text-align: center;">
#                         <a href="{request.build_absolute_uri('/loans/applications/')}" style="background-color: #4CAF50; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block; margin-top: 20px;">
#                             Approve Loan
#                         </a>
#                     </p>
#                 </div>
#             </body>
#         </html>
#         """
#         email = EmailMessage(
#             subject=subject,
#             body=message,
#             from_email=settings.EMAIL_HOST_USER,
#             # to=[settings.BOO_EMAIL, settings.ED_EMAIL],
#             to=[settings.ED_EMAIL],
#         )
#         email.content_subtype = "html"
#         email.send()

#         messages.success(
#             request, f"Loan {loan.id} approved by HOF.", extra_tags="bg-success"
#         )

#     elif loan.status == "hof_approved" and current_user.profile.role == "ed":
#         loan.status = "approved"
#         loan.approved_by_ed = current_user
#         loan.approved_date = timezone.now()
#         loan.save()

#         # Notify BOO, HOF, and Accountant with an HTML email
#         subject = f"Loan {loan.id} Fully Approved by ED"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
#                 <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
#                     <h2 style="color: #2c3e50; text-align: center;">Loan Approval Notification</h2>
#                     <p style="font-size: 16px; color: #34495e;">Dear Team,</p>
#                     <p style="font-size: 16px; color: #34495e;">We are pleased to inform you that the loan <strong style="color: #e74c3c;">{loan.id}</strong> for <strong style="color: #e74c3c;">{loan.borrower.full_name}</strong> (Amount: <strong style="color: #e74c3c;">UGX {loan.principal_amount:,.2f}</strong>) has been fully approved by <strong style="color: #e74c3c;">{current_user.username}</strong>.</p>
#                     <p style="font-size: 16px; color: #34495e;">Please proceed with the disbursement of the loan.</p>
#                     <p style="text-align: center;">
#                         <a href="{request.build_absolute_uri('/loans/disburse/')}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-size: 16px;">Disburse the Loan</a>
#                     </p>
#                 </div>
#             </body>
#         </html>
#         """
#         email = EmailMessage(
#             subject=subject,
#             body=message,
#             from_email=settings.EMAIL_HOST_USER,
#             to=[settings.BOO_EMAIL, settings.HOF_EMAIL, settings.ACCOUNTANT_EMAIL],
#         )
#         email.content_subtype = "html"
#         email.send()

#         messages.success(
#             request, f"Loan {loan.id} fully approved by ED.", extra_tags="bg-success"
#         )

#     else:
#         messages.error(
#             request,
#             "You are not authorized to approve this loan at this stage.",
#             extra_tags="bg-danger",
#         )
#         return redirect("loans:loan_applications")

#     return redirect("loans:loan_applications")


@login_required
def approve_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    current_user = request.user

    if loan.status == "pending" and current_user.profile.role == "boo":
        loan.status = "boo_approved"
        loan.approved_by_boo = current_user
        loan.save()

        messages.success(
            request, f"Loan {loan.id} approved by BOO.", extra_tags="bg-success"
        )

    elif loan.status == "boo_approved" and current_user.profile.role == "hof":
        loan.status = "hof_approved"
        loan.approved_by_hof = current_user
        loan.save()

        messages.success(
            request, f"Loan {loan.id} approved by HOF.", extra_tags="bg-success"
        )

    elif loan.status == "hof_approved" and current_user.profile.role == "ed":
        loan.status = "approved"
        loan.approved_by_ed = current_user
        loan.approved_date = timezone.now()
        loan.save()

        messages.success(
            request, f"Loan {loan.id} fully approved by ED.", extra_tags="bg-success"
        )

    else:
        messages.error(
            request,
            "You are not authorized to approve this loan at this stage.",
            extra_tags="bg-danger",
        )
        return redirect("loans:loan_applications")

    return redirect("loans:loan_applications")


# =================================== Approve All Loans View ===================================
@login_required
@admin_or_manager_or_staff_required
def approve_all_loans(request):
    current_user = request.user
    role = current_user.profile.role

    # Determine the current approval stage based on user role
    if role == "boo":
        pending_status = "pending"
        new_status = "boo_approved"
        approved_by_field = "approved_by_boo"
    elif role == "hof":
        pending_status = "boo_approved"
        new_status = "hof_approved"
        approved_by_field = "approved_by_hof"
    elif role == "ed":
        pending_status = "hof_approved"
        new_status = "approved"
        approved_by_field = "approved_by_ed"
    else:
        messages.error(
            request,
            "You are not authorized to approve loans at this stage.",
            extra_tags="bg-danger",
        )
        return redirect("loans:loan_applications")

    # Filter for loans at the current approval stage
    pending_loans = Loan.objects.filter(status=pending_status)

    if not pending_loans.exists():
        messages.info(
            request,
            f"No {pending_status.replace('_', ' ').title()} loans to approve.",
            extra_tags="bg-info",
        )
        return redirect("loans:loan_applications")

    # Approve each loan, setting the approved_by_field to the current_user
    for loan in pending_loans:
        loan.status = new_status
        setattr(loan, approved_by_field, current_user)
        if role == "ed":
            loan.approved_date = timezone.now()
        loan.save()

    messages.success(
        request,
        f"All {pending_status.replace('_', ' ').title()} loans have been approved successfully.",
        extra_tags="bg-success",
    )
    return redirect("loans:loan_applications")


# =================================== Reject Loan View ===================================
# @login_required
# @admin_or_manager_required
# def reject_loan(request, loan_id):
#     loan = get_object_or_404(Loan, id=loan_id)

#     # Check if the loan is already approved
#     if loan.status == "approved":
#         messages.error(
#             request,
#             f"Loan {loan.id} cannot be rejected because it is already approved.",
#             extra_tags="bg-warning",
#         )
#         return redirect("loans:loan_applications")

#     # Define the rejection process based on the current loan status
#     rejection_status = None
#     rejection_reason = "Please review this loan"

#     if loan.status == "boo_approved":
#         rejection_status = "hof_rejected"
#     elif loan.status == "hof_approved":
#         rejection_status = "ed_rejected"
#     else:
#         messages.error(
#             request,
#             f"Loan {loan.id} cannot be rejected because its status is {loan.status}.",
#             extra_tags="bg-warning",
#         )
#         return redirect("loans:loan_applications")

#     # Update loan status and reason for rejection
#     loan.status = rejection_status
#     loan.reason_for_rejection = rejection_reason
#     loan.save()

#     # Send appropriate email notifications
#     if rejection_status == "hof_rejected":
#         send_email_to_boo(loan)
#     elif rejection_status == "ed_rejected":
#         send_email_to_boo_and_hof(loan)

#     # Display success message
#     messages.info(request, f"Loan {loan.id} has been rejected.", extra_tags="bg-danger")

#     return redirect("loans:loan_applications")


# def send_email_to_boo(loan):
#     subject = f"Loan {loan.id} Rejected by HOF"
#     message = f"""
#     <html>
#         <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
#             <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
#                 <h2 style="color: #2c3e50; text-align: center;">Loan Rejection Notification</h2>
#                 <p style="font-size: 16px; color: #34495e;">Dear Team,</p>
#                 <p style="font-size: 16px; color: #34495e;">The loan <strong style="color: #e74c3c;">{loan.id}</strong> for <strong style="color: #e74c3c;">{loan.borrower.full_name}</strong> (Amount: <strong style="color: #e74c3c;">UGX {loan.principal_amount:,.2f}</strong>) has been rejected by the Head of Finance.</p>
#                 <p style="font-size: 16px; color: #34495e;">Please review the loan details and take appropriate actions.</p>
#             </div>
#         </body>
#     </html>
#     """
#     email = EmailMessage(
#         subject, message, settings.EMAIL_HOST_USER, [settings.BOO_EMAIL]
#     )
#     email.content_subtype = "html"
#     email.send()


# def send_email_to_boo_and_hof(loan):
#     subject = f"Loan {loan.id} Rejected by ED"
#     message = f"""
#     <html>
#         <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
#             <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
#                 <h2 style="color: #2c3e50; text-align: center;">Loan Rejection Notification</h2>
#                 <p style="font-size: 16px; color: #34495e;">Dear Team,</p>
#                 <p style="font-size: 16px; color: #34495e;">The loan <strong style="color: #e74c3c;">{loan.id}</strong> for <strong style="color: #e74c3c;">{loan.borrower.full_name}</strong> (Amount: <strong style="color: #e74c3c;">UGX {loan.principal_amount:,.2f}</strong>) has been rejected by the Executive Director.</p>
#                 <p style="font-size: 16px; color: #34495e;">Please review the loan details and take appropriate actions.</p>
#             </div>
#         </body>
#     </html>
#     """
#     email = EmailMessage(
#         subject,
#         message,
#         settings.EMAIL_HOST_USER,
#         [settings.BOO_EMAIL, settings.HOF_EMAIL],
#     )
#     email.content_subtype = "html"
#     email.send()


@login_required
@admin_or_manager_required
def reject_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)

    # Check if the loan is already approved
    if loan.status == "approved":
        messages.error(
            request,
            f"Loan {loan.id} cannot be rejected because it is already approved.",
            extra_tags="bg-warning",
        )
        return redirect("loans:loan_applications")

    # Define the rejection process based on the current loan status
    rejection_status = None
    rejection_reason = "Please review this loan"

    if loan.status == "boo_approved":
        rejection_status = "hof_rejected"
    elif loan.status == "hof_approved":
        rejection_status = "ed_rejected"
    else:
        messages.error(
            request,
            f"Loan {loan.id} cannot be rejected because its status is {loan.status}.",
            extra_tags="bg-warning",
        )
        return redirect("loans:loan_applications")

    # Update loan status and reason for rejection
    loan.status = rejection_status
    loan.reason_for_rejection = rejection_reason
    loan.save()

    # Display success message
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


# ===================================  loan_repayment_create_view  ===================================
# @login_required
# @admin_or_manager_or_staff_required
# @transaction.atomic  # Ensure database operations are within a transaction
# def loan_repayment_create_view(request):
#     form_title = "Repay Loans"

#     # Annotate loans with principal, interest, and penalty paid, and calculate remaining balances
#     loans_qs = (
#         Loan.objects.annotate(
#             principal_paid=Coalesce(
#                 Sum("repayments__principal_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             interest_paid=Coalesce(
#                 Sum("repayments__interest_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             penalty_paid=Coalesce(
#                 Sum("repayments__penalty_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             remaining_principal=F("principal_amount")
#             - Coalesce(
#                 Sum("repayments__principal_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             remaining_interest=F("total_interest")
#             - Coalesce(
#                 Sum("repayments__interest_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             remaining_penalty=Coalesce(
#                 Sum(
#                     "penalties__penalty_amount",
#                     filter=Q(penalties__is_paid=False),
#                     distinct=True,  # ✅ prevents duplicate counting
#                 ),
#                 Value(0, output_field=DecimalField()),
#             ),
#         )
#         .filter(
#             Q(remaining_principal__gt=0)
#             | Q(remaining_interest__gt=0)
#             | Q(remaining_penalty__gt=0),
#             status__in=["disbursed", "overdue"],
#         )
#         .select_related("borrower")
#         .distinct()
#     )

#     # Force queryset evaluation to avoid cursor persistence issues
#     loans = list(loans_qs)

#     # ✅ Filter out loans with missing/invalid borrower
#     loans = [loan for loan in loans if getattr(loan, "borrower", None)]

#     if request.method == "POST":
#         form = LoanRepaymentForm(request.POST)
#         if form.is_valid():
#             repayment = form.save(commit=False)
#             repayment.loan = form.cleaned_data["loan"]

#             # ✅ Guard against missing borrower before saving
#             if not getattr(repayment.loan, "borrower", None):
#                 messages.error(request, "This loan has no valid borrower attached.")
#                 return redirect("loans:loan_repayment_create")

#             repayment.save()

#             # After saving, update loan status
#             repayment.loan.update_status()

#             messages.success(
#                 request,
#                 "Loan repayment submitted successfully.",
#                 extra_tags="bg-success",
#             )
#             return redirect("loans:loan_repayment_create")
#         else:
#             messages.error(request, "Please correct the errors below.")
#     else:
#         form = LoanRepaymentForm()

#     return render(
#         request,
#         "loans/loan_repayment_form.html",
#         {
#             "form": form,
#             "form_title": form_title,
#             "loans": loans,  # Pass the safe loans list to the template
#         },
#     )


@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def loan_repayment_create_view(request):
    form_title = "Repay Loans"
    # Fetch loans with non-zero balances and valid status
    loans_qs = Loan.objects.filter(status__in=["disbursed", "overdue"]).select_related(
        "borrower"
    )
    # Calculate balances using model method and filter out fully paid loans
    loans = []
    for loan in loans_qs:
        if not getattr(loan, "borrower", None):
            continue  # Skip loans with missing borrowers
        balances = loan.calculate_remaining_balances()
        if (
            balances["principal_balance"] > 0
            or balances["interest_balance"] > 0
            or balances["penalty_balance"] > 0
        ):
            loan.remaining_principal = balances["principal_balance"]
            loan.remaining_interest = balances["interest_balance"]
            loan.remaining_penalty = balances["penalty_balance"]
            loans.append(loan)

    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.loan = form.cleaned_data["loan"]
            if not getattr(repayment.loan, "borrower", None):
                messages.error(request, "This loan has no valid borrower attached.")
                return redirect("loans:loan_repayment_create")
            repayment.save()
            repayment.loan.update_status()
            messages.success(
                request,
                "Loan repayment submitted successfully.",
                extra_tags="bg-success",
            )
            return redirect("loans:loan_repayment_create")
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
            "loans": loans,
        },
    )


# =================================== LoanPenaltyForm ===================================


# @login_required
# @admin_or_manager_or_staff_required
# @transaction.atomic
# def loan_penalty_create_view(request):
#     form_title = "Add Loan Penalty"

#     # Load loans with remaining balances
#     loans = (
#         Loan.objects.annotate(
#             principal_paid=Coalesce(
#                 Sum("repayments__principal_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             interest_paid=Coalesce(
#                 Sum("repayments__interest_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             penalty_paid=Coalesce(
#                 Sum("repayments__penalty_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             remaining_principal=F("principal_amount")
#             - Coalesce(
#                 Sum("repayments__principal_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             remaining_interest=F("total_interest")
#             - Coalesce(
#                 Sum("repayments__interest_payment"),
#                 Value(0, output_field=DecimalField()),
#             ),
#             remaining_penalty=Coalesce(
#                 Sum(
#                     "penalties__penalty_amount",
#                     filter=Q(penalties__is_paid=False),
#                     distinct=True,
#                 ),
#                 Value(0, output_field=DecimalField()),
#             ),
#         )
#         .filter(
#             Q(remaining_principal__gt=0)
#             | Q(remaining_interest__gt=0)
#             | Q(remaining_penalty__gt=0),
#             status__in=["disbursed", "overdue"],
#         )
#         .select_related("borrower")
#         .distinct()
#     )

#     loans = list(loans)  # Materialize queryset

#     if request.method == "POST":
#         form = LoanPenaltyForm(request.POST, user=request.user)
#         if form.is_valid():
#             penalty = form.save(commit=False)
#             penalty.created_by = request.user
#             penalty.save()

#             # Update loan status
#             penalty.loan.update_status()

#             messages.success(
#                 request,
#                 f"Penalty of {penalty.penalty_amount:,.2f} added to Loan {penalty.loan.id} successfully.",
#                 extra_tags="bg-success",
#             )
#             return redirect("loans:loan_penalty_create")
#         else:
#             messages.error(request, "Please correct the errors below.")
#     else:
#         form = LoanPenaltyForm(user=request.user)

#     return render(
#         request,
#         "loans/loan_penalty_form.html",
#         {
#             "form": form,
#             "form_title": form_title,
#             "loans": loans,
#         },
#     )


@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def loan_penalty_create_view(request):
    form_title = "Add Loan Penalty"
    # Fetch loans with non-zero balances and valid status
    loans_qs = Loan.objects.filter(status__in=["disbursed", "overdue"]).select_related(
        "borrower"
    )
    # Calculate balances using model method and filter out fully paid loans
    loans = []
    for loan in loans_qs:
        if not getattr(loan, "borrower", None):
            continue  # Skip loans with missing borrowers
        balances = loan.calculate_remaining_balances()
        if (
            balances["principal_balance"] > 0
            or balances["interest_balance"] > 0
            or balances["penalty_balance"] > 0
        ):
            loan.remaining_principal = balances["principal_balance"]
            loan.remaining_interest = balances["interest_balance"]
            loan.remaining_penalty = balances["penalty_balance"]
            loans.append(loan)

    if request.method == "POST":
        form = LoanPenaltyForm(request.POST, user=request.user)
        if form.is_valid():
            penalty = form.save(commit=False)
            penalty.created_by = request.user
            penalty.save()
            # Update loan status
            penalty.loan.update_status()
            messages.success(
                request,
                f"Penalty of {penalty.penalty_amount:,.2f} added to Loan {penalty.loan.id} successfully.",
                extra_tags="bg-success",
            )
            return redirect("loans:loan_penalty_create")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LoanPenaltyForm(user=request.user)
    return render(
        request,
        "loans/loan_penalty_form.html",
        {
            "form": form,
            "form_title": form_title,
            "loans": loans,
        },
    )


# ===================================  loan_detail_view  ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_detail_view(request, loan_id):
    # Fetch the loan instance
    loan = get_object_or_404(Loan, id=loan_id)

    # Call to calculate remaining balances
    remaining_balances = loan.calculate_remaining_balances()

    # Fetch all repayments associated with the loan
    repayments = loan.repayments.all()  # Access repayments via related_name

    # Calculate totals for principal and interest
    totals = repayments.aggregate(
        total_principal=Sum("principal_payment"),
        total_interest=Sum("interest_payment"),
        total_penalty=Sum("penalty_payment"),
    )

    # Get borrower's full name
    borrower_name = loan.borrower.full_name
    borrower_reg_no = loan.borrower.reg_number

    # Set up the form title for the view
    form_title = f"{borrower_name} | Loan id: ({loan.id}) | Reg No: {borrower_reg_no}"

    # Render the loan detail template with necessary context
    return render(
        request,
        "loans/loan_detail.html",
        {
            "loan": loan,
            "remaining_principal": remaining_balances["principal_balance"],
            "remaining_interest": remaining_balances["interest_balance"],
            "remaining_penalty": remaining_balances["penalty_balance"],
            "repayments": repayments,
            "borrower_name": borrower_name,
            "total_principal": totals["total_principal"] or 0,
            "total_interest": totals["total_interest"] or 0,
            "total_penalty": totals["total_penalty"] or 0,
            "form_title": form_title,
        },
    )


@login_required
@admin_or_manager_required
def delete_repayment(request, repayment_id):
    repayment = get_object_or_404(LoanRepayment, id=repayment_id)

    if request.method == "POST":
        repayment.delete()
        messages.success(
            request,
            "Repayment deleted successfully.",
            extra_tags="bg-success",
        )

    return redirect(request.META.get("HTTP_REFERER", "loans:loan_list"))


# =================================== Chart of Accounts List View ===================================
@login_required
@admin_or_manager_or_staff_required
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
                    # Call process_and_import_accounts_data function
                    errors = process_and_import_accounts_data(excel_file)
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
def process_and_import_accounts_data(excel_file):
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


# =================================== ledger_report view ===================================
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
@admin_or_manager_or_staff_required
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


# =================================== Loan Aging Report view ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_aging_report(request):
    today = timezone.now().date()

    # Define aging buckets
    aging_buckets = {
        "Current (0 Days)": [],
        "0-30 Days (WATCH)": [],
        "31-60 Days (SUBSTANDARD)": [],
        "61-90 Days (SUBSTANDARD)": [],
        "91-120 Days (DOUBTFUL)": [],
        "121-180 Days (DOUBTFUL)": [],
        "181-365 Days (LOSS)": [],
        "Over 365 Days (LOSS)": [],
    }

    # Initialize totals
    grand_totals = {
        "total_principal": Decimal("0.00"),
        "total_principal_due": Decimal("0.00"),
        "total_interest_due": Decimal("0.00"),
        "total_penalty_due": Decimal("0.00"),
        "total_outstanding_balance": Decimal("0.00"),
        "total_paid": Decimal("0.00"),
    }

    # Fetch disbursed and overdue loans
    disbursed_loans = Loan.objects.filter(
        status__in=["overdue", "disbursed"],
        due_date__isnull=False,
    ).select_related("borrower")

    bucket_totals = {
        key: {
            "total_principal": Decimal("0.00"),
            "total_principal_due": Decimal("0.00"),
            "total_interest_due": Decimal("0.00"),
            "total_penalty_due": Decimal("0.00"),
            "total_outstanding_balance": Decimal("0.00"),
            "total_paid": Decimal("0.00"),
        }
        for key in aging_buckets
    }

    for loan in disbursed_loans:
        try:
            # Calculate remaining balances
            remaining_balances = loan.calculate_remaining_balances()
            remaining_principal = remaining_balances["principal_balance"]
            remaining_interest = remaining_balances["interest_balance"]
            penalty_balance = remaining_balances["penalty_balance"]
            outstanding_balance = (
                remaining_principal + remaining_interest + penalty_balance
            )

            # Filter loans with outstanding balance > 0
            if outstanding_balance <= 0:
                continue

            # Calculate days overdue, ensuring non-negative values
            days_overdue = max((today - loan.due_date).days, 0) if loan.due_date else 0

            loan_info = {
                "loan_id": loan.id,
                "borrower": loan.borrower.full_name,
                "principal_amount": loan.principal_amount,
                "interest_rate": loan.interest_rate,
                "loan_period_months": loan.loan_period_months,
                "start_date": loan.start_date,
                "due_date": loan.due_date,
                "days_overdue": days_overdue,
                "principal_due": remaining_principal,
                "interest_due": remaining_interest,
                "penalty_due": penalty_balance,
                "outstanding_balance": outstanding_balance,
                "total_paid": sum(
                    repayment.principal_payment + repayment.interest_payment
                    for repayment in loan.repayments.all()
                )
                or Decimal("0.00"),
            }

            # Categorize loans into buckets
            bucket_key = (
                "Current (0 Days)"
                if days_overdue <= 0
                else (
                    "0-30 Days (WATCH)"
                    if 0 < days_overdue <= 30
                    else (
                        "31-60 Days (SUBSTANDARD)"
                        if 31 <= days_overdue <= 60
                        else (
                            "61-90 Days (SUBSTANDARD)"
                            if 61 <= days_overdue <= 90
                            else (
                                "91-120 Days (DOUBTFUL)"
                                if 91 <= days_overdue <= 120
                                else (
                                    "121-180 Days (DOUBTFUL)"
                                    if 121 <= days_overdue <= 180
                                    else (
                                        "181-365 Days (LOSS)"
                                        if 181 <= days_overdue <= 365
                                        else "Over 365 Days (LOSS)"
                                    )
                                )
                            )
                        )
                    )
                )
            )

            aging_buckets[bucket_key].append(loan_info)

            # Update bucket totals
            bucket_totals[bucket_key]["total_principal"] += loan.principal_amount
            bucket_totals[bucket_key]["total_principal_due"] += remaining_principal
            bucket_totals[bucket_key]["total_interest_due"] += remaining_interest
            bucket_totals[bucket_key]["total_penalty_due"] += penalty_balance
            bucket_totals[bucket_key][
                "total_outstanding_balance"
            ] += outstanding_balance
            bucket_totals[bucket_key]["total_paid"] += loan_info["total_paid"]

            # Update grand totals
            grand_totals["total_principal"] += loan.principal_amount
            grand_totals["total_principal_due"] += remaining_principal
            grand_totals["total_interest_due"] += remaining_interest
            grand_totals["total_penalty_due"] += penalty_balance
            grand_totals["total_outstanding_balance"] += outstanding_balance
            grand_totals["total_paid"] += loan_info["total_paid"]

        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    # Sort and paginate each bucket
    paginated_buckets = {}
    for bucket_key in aging_buckets:
        # Sort by start_date
        aging_buckets[bucket_key] = sorted(
            aging_buckets[bucket_key],
            key=lambda x: x["start_date"] or timezone.datetime.min,
        )
        # Paginate
        paginator = Paginator(aging_buckets[bucket_key], 10)  # 10 loans per page
        page_number = request.GET.get(
            f'page_{bucket_key.replace(" ", "_").replace("(", "").replace(")", "")}'
        )
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        paginated_buckets[bucket_key] = page_obj

    return render(
        request,
        "loans/loan_aging_report.html",
        {
            "paginated_buckets": paginated_buckets,
            "bucket_totals": bucket_totals,
            "grand_totals": grand_totals,
            "table_title": "Loan Aging Report",
        },
    )


# =================================== Loan Arrears Report view ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_arrears_report(request):
    today = timezone.now().date()

    # Define arrears categories with human-readable names
    arrears_categories = {
        "0-30 Days (WATCH)": [],
        "31-60 Days (SUBSTANDARD)": [],
        "61-90 Days (SUBSTANDARD)": [],
        "91-120 Days (DOUBTFUL)": [],
        "121-180 Days (DOUBTFUL)": [],
        "181-365 Days (LOSS)": [],
        "Over 365 Days (LOSS)": [],
    }

    # Fetch and categorize overdue loans
    overdue_loans = (
        Loan.objects.filter(
            # status="disbursed",
            status__in=["overdue", "disbursed"],
            due_date__isnull=False,
            due_date__lt=today,
        )
        .annotate(
            total_repayment=Sum(
                F("repayments__principal_payment") + F("repayments__interest_payment")
            ),
            calculated_interest=Sum("repayments__interest_payment"),
        )
        .select_related("borrower")
        .values(
            "id",
            "borrower__full_name",
            "principal_amount",
            "start_date",
            "due_date",
            "interest_rate",
            "loan_period_months",
        )
    )

    # Process each loan to calculate overdue balances and categorize by days overdue
    for loan in overdue_loans:
        loan_id = loan["id"]
        borrower = loan["borrower__full_name"]
        principal_amount = loan["principal_amount"]
        start_date = loan["start_date"]
        due_date = loan["due_date"]
        interest_rate = loan["interest_rate"]
        loan_period_months = loan["loan_period_months"]

        # Fetch remaining balances
        remaining_balances = Loan.objects.get(id=loan_id).calculate_remaining_balances()
        remaining_principal = remaining_balances["principal_balance"]
        remaining_interest = remaining_balances["interest_balance"]
        outstanding_balance = remaining_principal + remaining_interest

        # Filter loans with outstanding balance > 0
        if outstanding_balance <= 0:
            continue

        # Calculate days overdue
        days_overdue = (today - due_date).days

        # Determine the arrears category and loan status
        if 0 < days_overdue <= 30:
            category = "0-30 Days (WATCH)"
            status = "Watch"
        elif 31 <= days_overdue <= 60:
            category = "31-60 Days (SUBSTANDARD)"
            status = "Substandard"
        elif 61 <= days_overdue <= 90:
            category = "61-90 Days (SUBSTANDARD)"
            status = "Substandard"
        elif 91 <= days_overdue <= 120:
            category = "91-120 Days (DOUBTFUL)"
            status = "Doubtful"
        elif 121 <= days_overdue <= 180:
            category = "121-180 Days (DOUBTFUL)"
            status = "Doubtful"
        elif 181 <= days_overdue <= 365:
            category = "181-365 Days (LOSS)"
            status = "Loss"
        else:
            category = "Over 365 Days (LOSS)"
            status = "Loss"

        # Build the loan information dictionary
        loan_info = {
            "loan_id": loan_id,
            "borrower": borrower,
            "principal_amount": principal_amount,
            "start_date": start_date,
            "due_date": due_date,
            "interest_rate": interest_rate,
            "loan_period_months": loan_period_months,
            "days_overdue": days_overdue,
            "principal_due": remaining_principal,
            "interest_due": remaining_interest,
            "outstanding_balance": outstanding_balance,
            "status": status,
        }

        # Append loan to the appropriate arrears category
        arrears_categories[category].append(loan_info)

    # Render the report to the template
    return render(
        request,
        "loans/loan_arrears_report.html",
        {
            "arrears_categories": arrears_categories,
            "table_title": "Loan Arrears Report",
        },
    )


# =================================== loan_portfolio_report view ===================================


@login_required
@admin_or_manager_or_staff_required
def loan_portfolio_report(request):
    today = timezone.now().date()

    # Fetch loans with borrower data
    loans = Loan.objects.select_related("borrower").all()

    loan_data = []
    total_principal = Decimal("0.00")
    total_remaining_principal = Decimal("0.00")
    total_remaining_interest = Decimal("0.00")
    total_penalty_balance = Decimal("0.00")
    total_remaining_balance = Decimal("0.00")

    for loan in loans:
        try:
            # Calculate remaining balances
            remaining_balances = loan.calculate_remaining_balances()
            remaining_principal = remaining_balances["principal_balance"]
            remaining_interest = remaining_balances["interest_balance"]
            penalty_balance = remaining_balances["penalty_balance"]
            total_remaining_balance_for_loan = (
                remaining_principal + remaining_interest + penalty_balance
            )

            # Only include loans with positive remaining balance
            if total_remaining_balance_for_loan > 0:
                # Calculate overdue days
                days_overdue = (
                    (today - loan.due_date).days
                    if loan.due_date and loan.due_date < today
                    else 0
                )

                # Sum totals
                total_principal += loan.principal_amount
                total_remaining_principal += remaining_principal
                total_remaining_interest += remaining_interest
                total_penalty_balance += penalty_balance
                total_remaining_balance += total_remaining_balance_for_loan

                loan_info = {
                    "loan_id": loan.id,
                    "borrower": loan.borrower.full_name,
                    "principal_amount": loan.principal_amount,
                    "interest_rate": loan.interest_rate,
                    "loan_period_months": loan.loan_period_months,
                    "remaining_principal": remaining_principal,
                    "remaining_interest": remaining_interest,
                    "penalty_balance": penalty_balance,
                    "total_remaining_balance": total_remaining_balance_for_loan,
                    "start_date": loan.start_date,
                    "due_date": loan.due_date,
                    "days_overdue": days_overdue,
                }
                loan_data.append(loan_info)
        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    # Sort loan_data by start_date
    loan_data = sorted(
        loan_data, key=lambda x: x["start_date"] or timezone.datetime.min
    )

    # Paginate loan_data
    paginator = Paginator(loan_data, 50)  # 50 loans per page
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(
        request,
        "loans/loan_portfolio_report.html",
        {
            "page_obj": page_obj,
            "table_title": "Loan Portfolio Report",
            "total_principal": total_principal,
            "total_remaining_principal": total_remaining_principal,
            "total_remaining_interest": total_remaining_interest,
            "total_penalty_balance": total_penalty_balance,
            "total_remaining_balance": total_remaining_balance,
        },
    )


# =================================== portfolio_at_risk view ===================================
@login_required
@admin_or_manager_or_staff_required
def portfolio_at_risk(request):
    # Fetch all loans
    loans = Loan.objects.all().order_by("id")

    # Get today's date to calculate overdue days
    today = timezone.now().date()

    # Initialize values for PAR calculations
    total_outstanding_loans = 0
    total_past_due_30 = 0
    total_past_due_60 = 0
    total_past_due_90 = 0

    loan_data = []

    # Calculate days overdue, remaining principal, interest, and PAR totals for each loan
    for loan in loans:
        # Call to calculate remaining balances for the loan
        remaining_balances = (
            loan.calculate_remaining_balances()
        )  # Make sure this method is defined in the model
        remaining_principal = remaining_balances["principal_balance"]
        remaining_interest = remaining_balances["interest_balance"]

        # Calculate the number of days overdue, if any
        if loan.due_date and loan.due_date < today:
            days_overdue = (today - loan.due_date).days
        else:
            days_overdue = (
                0  # Set to 0 if the due date is in the future or loan is on time
            )

        # Add data to loan_data list
        loan_info = {
            "loan_id": loan.id,
            "borrower": loan.borrower.full_name,  # Assuming Loan has a ForeignKey to a Borrower model
            "principal_amount": loan.principal_amount,
            "interest_rate": loan.interest_rate,
            "loan_period_months": loan.loan_period_months,
            "remaining_principal": remaining_principal,
            "remaining_interest": remaining_interest,
            "total_remaining_balance": remaining_principal + remaining_interest,
            "start_date": loan.start_date,
            "due_date": loan.due_date,
            "days_overdue": days_overdue,
        }

        # Add the loan_info to the total outstanding loan amounts
        total_outstanding_loans += remaining_principal + remaining_interest
        if days_overdue >= 30:
            total_past_due_30 += remaining_principal + remaining_interest
        if days_overdue >= 60:
            total_past_due_60 += remaining_principal + remaining_interest
        if days_overdue >= 90:
            total_past_due_90 += remaining_principal + remaining_interest

        loan_data.append(loan_info)

    # Calculate PAR for different overdue periods
    if total_outstanding_loans > 0:
        par_30 = (total_past_due_30 / total_outstanding_loans) * 100
        par_60 = (total_past_due_60 / total_outstanding_loans) * 100
        par_90 = (total_past_due_90 / total_outstanding_loans) * 100
    else:
        par_30 = par_60 = par_90 = 0

    # Prepare context for the report
    context = {
        "par_30": par_30,
        "par_60": par_60,
        "par_90": par_90,
        "loan_data": loan_data,  # Use loan_data in the context
        "table_title": "Loan Portfolio at Risk Report",
    }

    return render(request, "loans/portfolio_at_risk_report.html", context)


# =================================== non_performing_loans view ===================================


@login_required
@admin_or_manager_or_staff_required
def non_performing_loans(request):
    # Get today's date
    today = timezone.now().date()

    # Fetch loans that are overdue or potentially non-performing
    loans_with_balance = (
        Loan.objects.filter(
            Q(status="overdue")
            | Q(due_date__lt=today, status__in=["disbursed", "approved"])
        )
        .select_related("borrower", "account")
        .prefetch_related("repayments")
    )

    # Filter loans with outstanding balance > 0
    non_performing_loans = [
        loan
        for loan in loans_with_balance
        if (balances := loan.calculate_remaining_balances())["principal_balance"]
        + balances["interest_balance"]
        > 0
    ]

    # Add display attributes for template
    for loan in non_performing_loans:
        balances = loan.calculate_remaining_balances()
        loan.outstanding_balance = (
            balances["principal_balance"] + balances["interest_balance"]
        )
        loan.days_overdue = (
            (today - loan.due_date).days
            if loan.due_date and loan.due_date < today
            else 0
        )

    context = {
        "non_performing_loans": non_performing_loans,
        "today": today,
        "table_title": "Non-Performing Loans with Outstanding Balance",
    }
    return render(request, "loans/non_performing_loans.html", context)


# =================================== import_loan_data view ===================================
@login_required
@admin_required
def import_loan_data(request):
    if request.method == "POST":
        form = ImportLoansForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES.get("excel_file")
            if excel_file and excel_file.name.endswith(".xlsx"):
                try:
                    # Call process_and_import_loan_data function
                    errors = process_and_import_loan_data(excel_file)
                    if errors:
                        for error in errors:
                            messages.error(request, error, extra_tags="bg-danger")
                            logger.error(f"Import error: {error}")  # Log each error
                    else:
                        messages.success(
                            request,
                            "Data imported successfully!",
                            extra_tags="bg-success",
                        )
                except Exception as e:
                    error_message = f"Error importing data: {e}"
                    messages.error(request, error_message, extra_tags="bg-danger")
                    logger.error(error_message, exc_info=True)  # Log the exception
                return redirect("loans:loan_applications")
            else:
                messages.error(
                    request, "Please upload a valid Excel file.", extra_tags="bg-danger"
                )
    else:
        form = ImportLoansForm()
    return render(
        request,
        "loans/import_loans.html",
        {"form_name": "Import Loans - Excel", "form": form},
    )


def process_and_import_loan_data(excel_file):
    errors = []
    try:
        wb = load_workbook(excel_file)
        sheet = wb.active  # Use the active sheet

        for row_num, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            reg_number = row[0].value
            full_name = row[1].value
            picture = row[2].value
            mobile_telephone = row[3].value
            principal_amount = row[4].value
            interest_rate = row[5].value
            start_date = row[6].value
            loan_period_months = row[7].value
            # status = row[8].value
            interest_method = row[8].value

            if full_name:
                try:
                    client, created = Client.objects.get_or_create(
                        reg_number=reg_number,
                        defaults={
                            "full_name": full_name,
                            "picture": picture,
                            "mobile_telephone": mobile_telephone,
                        },
                    )
                    Loan.objects.create(
                        borrower=client,
                        principal_amount=principal_amount,
                        interest_rate=interest_rate,
                        start_date=start_date,
                        loan_period_months=loan_period_months,
                        # status=status,
                        interest_method=interest_method,
                    )
                except Exception as e:
                    error_message = f"Error on row {row_num}: {e}"
                    errors.append(error_message)
                    logger.error(
                        error_message, exc_info=True
                    )  # Log each row-specific error
            else:
                error_message = f"Missing full name on row {row_num}"
                errors.append(error_message)
                logger.warning(error_message)  # Log a warning for missing full name

    except Exception as e:
        error_message = f"Failed to process the Excel file: {e}"
        errors.append(error_message)
        logger.error(
            error_message, exc_info=True
        )  # Log the exception for file processing failure

    return errors


# =================================== loan_reports_dashboard view ===================================
@login_required
def loan_reports_dashboard(request):
    """
    Renders the reports dashboard with report cards for users with the 'administrator' role.
    """
    context = {"form_title": "Loan Management Dashboard"}
    return render(request, "loans/loan_reports.html", context)


# =================================== client_loan_statement view ===================================
@login_required
@admin_or_manager_or_staff_required
def client_loan_statement(request):
    # Fetch only clients with loans that have outstanding balances
    clients = (
        Client.objects.filter(loans__status__in=["disbursed", "overdue", "repaid"])
        .distinct()
        .order_by("full_name")
    )

    client = None
    statement_data = None

    if request.method == "POST":
        client_id = request.POST.get("client_id")
        if client_id:
            client = get_object_or_404(Client, id=client_id)
            loans = (
                Loan.objects.filter(borrower=client)
                .select_related("account")
                .order_by("-created_at")
            )

            statement_data = []
            for loan in loans:
                # Fetch all repayments
                repayments = loan.repayments.all().order_by("repayment_date")

                # Sum principal, interest, and penalty payments; coalesce None -> 0
                totals = repayments.aggregate(
                    total_principal=Sum("principal_payment"),
                    total_interest=Sum("interest_payment"),
                    total_penalty=Sum("penalty_payment"),
                )
                total_principal_paid = totals["total_principal"] or Decimal("0.00")
                total_interest_paid = totals["total_interest"] or Decimal("0.00")
                total_penalty_paid = totals["total_penalty"] or Decimal("0.00")

                # Calculate remaining balances
                principal_balance = loan.principal_amount - total_principal_paid
                interest_balance = loan.total_interest - total_interest_paid

                # Total penalties applied to loan
                total_penalties = loan.penalties.aggregate(total=Sum("penalty_amount"))[
                    "total"
                ] or Decimal("0.00")
                penalty_balance = total_penalties - total_penalty_paid

                # Fetch transactions and payment schedule
                transactions = loan.transactions.all().order_by("transaction_date")
                payment_schedule = loan.generate_payment_schedule()

                # Assemble loan data
                loan_data = {
                    "loan": loan,
                    "repayments": repayments,
                    "transactions": transactions,
                    "principal_balance": principal_balance,
                    "interest_balance": interest_balance,
                    "penalty_balance": penalty_balance,
                    "total_balance": principal_balance
                    + interest_balance
                    + penalty_balance,
                    "payment_schedule": payment_schedule,
                }
                statement_data.append(loan_data)

    context = {
        "clients": clients,
        "client": client,
        "statement_data": statement_data,
    }

    return render(request, "loans/loan_statement.html", context)


# =================================== loan_due_overdue_report view===================================


@login_required
@admin_or_manager_or_staff_required
def loan_due_overdue_report(request):
    try:
        timezone.activate(pytz.timezone("Africa/Nairobi"))
    except pytz.exceptions.UnknownTimeZoneError:
        timezone.activate(pytz.UTC)

    # Get selected date from GET parameters or default to today
    selected_date_str = request.GET.get("selected_date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # Check cache
    cache_key = f"loan_due_overdue_report_{selected_date.strftime('%Y-%m-%d')}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, "loans/due_overdue_report.html", cached_data)

    # Optimize database query with select_related and prefetch_related
    disbursed_loans = (
        Loan.objects.filter(status__in=["disbursed", "overdue"])
        .select_related("borrower")
        .prefetch_related("repayments", "penalties")
        .order_by("id")
    )
    due_loans = []
    overdue_loans = []

    for loan in disbursed_loans:
        try:
            # Validate loan data
            if not loan.disbursement_date or loan.loan_period_months <= 0:
                continue

            # Calculate balances
            balances = loan.calculate_remaining_balances()
            total_balance = (
                balances["principal_balance"]
                + balances["interest_balance"]
                + balances["penalty_balance"]
            )
            if total_balance <= 0:
                continue

            # Generate payment schedule
            schedule = loan.generate_payment_schedule()
            if not schedule:
                continue

            # Normalize dates in schedule to date objects
            payments = [
                {
                    **p,
                    "payment_due_date": (
                        p["payment_due_date"].date()
                        if isinstance(p["payment_due_date"], datetime)
                        else p["payment_due_date"]
                    ),
                }
                for p in schedule
                if isinstance(p["payment_due_date"], (date, datetime))
                and p["principal_payment"] + p["interest_payment"] > 0
            ]

            # Check for overdue loans (due date before selected_date)
            if loan.due_date and loan.due_date < selected_date:
                days_overdue = (selected_date - loan.due_date).days
                total_amount_due = Decimal(total_balance)
                total_amount_due_balance = min(
                    loan.calculate_total_amount_due_balance(
                        due_date=selected_date, total_amount_due=total_amount_due
                    ),
                    total_balance,  # Cap at total_balance
                )
                if total_amount_due_balance <= 0:
                    continue
                logger.info(
                    f"Overdue Loan {loan.id}: total_balance={total_balance:,.2f}, "
                    f"total_amount_due={total_amount_due:,.2f}, "
                    f"total_amount_due_balance={total_amount_due_balance:,.2f}"
                )
                overdue_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_balance": total_balance,
                        "disbursement_date": loan.disbursement_date,
                        "maturity_due_date": loan.due_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                        "days_overdue": days_overdue,
                    }
                )
                continue

            # Check for overdue payments (payment due before selected_date)
            overdue_payments = [
                p for p in payments if p["payment_due_date"] < selected_date
            ]
            if overdue_payments:
                earliest_due_date = min(p["payment_due_date"] for p in overdue_payments)
                days_overdue = (selected_date - earliest_due_date).days
                total_amount_due = Decimal(
                    min(
                        sum(
                            p["principal_payment"] + p["interest_payment"]
                            for p in overdue_payments
                        ),
                        total_balance,
                    )
                )
                total_amount_due_balance = min(
                    loan.calculate_total_amount_due_balance(
                        due_date=selected_date, total_amount_due=total_amount_due
                    ),
                    total_balance,  # Cap at total_balance
                )
                if total_amount_due_balance <= 0:
                    continue
                logger.info(
                    f"Overdue Payment Loan {loan.id}: total_balance={total_balance:,.2f}, "
                    f"total_amount_due={total_amount_due:,.2f}, "
                    f"total_amount_due_balance={total_amount_due_balance:,.2f}"
                )
                overdue_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_balance": total_balance,
                        "disbursement_date": loan.disbursement_date,
                        "maturity_due_date": loan.due_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                        "days_overdue": days_overdue,
                    }
                )
                continue

            # Check for due loans (payment due on selected_date or loan due_date matches selected_date)
            due_payments = [
                p for p in payments if p["payment_due_date"] == selected_date
            ]
            is_due_on_date = loan.due_date == selected_date
            if due_payments or is_due_on_date:
                total_amount_due = Decimal(
                    min(
                        sum(
                            p["principal_payment"] + p["interest_payment"]
                            for p in due_payments
                        ),
                        total_balance,
                    )
                    if due_payments
                    else total_balance
                )
                total_amount_due_balance = min(
                    loan.calculate_total_amount_due_balance(
                        due_date=selected_date, total_amount_due=total_amount_due
                    ),
                    total_balance,  # Cap at total_balance
                )
                if total_amount_due_balance <= 0:
                    continue
                logger.info(
                    f"Due Loan {loan.id}: total_balance={total_balance:,.2f}, "
                    f"total_amount_due={total_amount_due:,.2f}, "
                    f"total_amount_due_balance={total_amount_due_balance:,.2f}"
                )
                due_loans.append(
                    {
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_balance": total_balance,
                        "due_payment": due_payments[0] if due_payments else None,
                        "disbursement_date": loan.disbursement_date,
                        "maturity_due_date": loan.due_date,
                        "total_amount_due": total_amount_due,
                        "total_amount_due_balance": total_amount_due_balance,
                    }
                )

        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {str(e)}")
            continue

    # Pagination
    due_paginator = Paginator(due_loans, 10)
    overdue_paginator = Paginator(overdue_loans, 10)
    due_page = request.GET.get("due_page", 1)
    overdue_page = request.GET.get("overdue_page", 1)

    try:
        due_loans_paginated = due_paginator.page(due_page)
    except PageNotAnInteger:
        due_loans_paginated = due_paginator.page(1)
    except EmptyPage:
        due_loans_paginated = due_paginator.page(due_paginator.num_pages)

    try:
        overdue_loans_paginated = overdue_paginator.page(overdue_page)
    except PageNotAnInteger:
        overdue_loans_paginated = overdue_paginator.page(1)
    except EmptyPage:
        overdue_loans_paginated = overdue_paginator.page(overdue_paginator.num_pages)

    # Calculate totals efficiently
    due_loans_count = len(due_loans)
    due_loans_total_amount = sum(loan["total_amount_due"] for loan in due_loans)
    due_loans_total_balance = sum(loan["total_balance"] for loan in due_loans)
    due_loans_total_due_balance = sum(
        loan["total_amount_due_balance"] for loan in due_loans
    )
    due_loans_total_penalty_balance = sum(loan["penalty_balance"] for loan in due_loans)
    overdue_loans_count = len(overdue_loans)
    overdue_loans_total_amount = sum(loan["total_amount_due"] for loan in overdue_loans)
    overdue_loans_total_balance = sum(loan["total_balance"] for loan in overdue_loans)
    overdue_loans_total_due_balance = sum(
        loan["total_amount_due_balance"] for loan in overdue_loans
    )
    overdue_loans_total_penalty_balance = sum(
        loan["penalty_balance"] for loan in overdue_loans
    )

    context = {
        "due_loans": due_loans_paginated,
        "due_loans_count": due_loans_count,
        "due_loans_total_amount": due_loans_total_amount,
        "due_loans_total_balance": due_loans_total_balance,
        "due_loans_total_due_balance": due_loans_total_due_balance,
        "due_loans_total_penalty_balance": due_loans_total_penalty_balance,
        "overdue_loans": overdue_loans_paginated,
        "overdue_loans_count": overdue_loans_count,
        "overdue_loans_total_amount": overdue_loans_total_amount,
        "overdue_loans_total_balance": overdue_loans_total_balance,
        "overdue_loans_total_due_balance": overdue_loans_total_due_balance,
        "overdue_loans_total_penalty_balance": overdue_loans_total_penalty_balance,
        "selected_date": selected_date,
    }

    # Cache the context
    cache.set(cache_key, context, timeout=3600)  # Cache for 1 hour

    return render(request, "loans/due_overdue_report.html", context)
