import logging
from datetime import date, datetime
from decimal import ROUND_DOWN, Decimal
from datetime import timedelta
import pytz
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q, Sum
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
    LoanPenalty,
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
# @transaction.atomic
# def loan_repayment_create_view(request):
#     form_title = "Repay Loans"
#     # Fetch loans with non-zero balances and valid status
#     loans_qs = Loan.objects.filter(status__in=["disbursed", "overdue"]).select_related(
#         "borrower"
#     )
#     # Calculate balances using model method and filter out fully paid loans
#     loans = []
#     for loan in loans_qs:
#         if not getattr(loan, "borrower", None):
#             continue  # Skip loans with missing borrowers
#         balances = loan.calculate_remaining_balances()
#         if (
#             balances["principal_balance"] > 0
#             or balances["interest_balance"] > 0
#             or balances["penalty_balance"] > 0
#         ):
#             loan.remaining_principal = balances["principal_balance"]
#             loan.remaining_interest = balances["interest_balance"]
#             loan.remaining_penalty = balances["penalty_balance"]
#             loans.append(loan)

#     if request.method == "POST":
#         form = LoanRepaymentForm(request.POST)
#         if form.is_valid():
#             repayment = form.save(commit=False)
#             repayment.loan = form.cleaned_data["loan"]
#             if not getattr(repayment.loan, "borrower", None):
#                 messages.error(request, "This loan has no valid borrower attached.")
#                 return redirect("loans:loan_repayment_create")
#             repayment.save()
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
#             "loans": loans,
#         },
#     )


@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def loan_repayment_create_view(request):
    form_title = "Repay Loans"

    # Fetch loans with valid statuses
    loans_qs = Loan.objects.filter(status__in=["disbursed", "overdue"]).select_related(
        "borrower"
    )

    # Apply balance filtering (same as penalty view)
    loans = []
    for loan in loans_qs:
        if not getattr(loan, "borrower", None):
            continue  # Skip loans with missing borrowers

        balances = loan.calculate_remaining_balances()

        # Only add loans that actually have balances left
        if (
            balances["principal_balance"] > 0
            or balances["interest_balance"] > 0
            or balances["penalty_balance"] > 0
        ):
            loan.remaining_principal = balances["principal_balance"]
            loan.remaining_interest = balances["interest_balance"]
            loan.remaining_penalty = balances["penalty_balance"]
            loans.append(loan)

    # -----------------------
    # PROCESS FORM
    # -----------------------
    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)

        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.loan = form.cleaned_data["loan"]

            if not getattr(repayment.loan, "borrower", None):
                messages.error(request, "This loan has no valid borrower attached.")
                return redirect("loans:loan_repayment_create")

            repayment.save()

            # Update loan status
            repayment.loan.update_status()

            messages.success(
                request,
                "Loan repayment submitted successfully.",
                extra_tags="bg-success",
            )

            return redirect("loans:loan_repayment_create")

        else:
            messages.error(
                request, "Please correct the errors below.", extra_tags="bg-danger"
            )

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

# @login_required
# @admin_or_manager_or_staff_required
# def loan_aging_report(request):
#     today = timezone.now().date()

#     # Updated buckets - combined first two
#     aging_buckets = {
#         "0-30 Days (Performing / Watch)": [],
#         "31-60 Days (SUBSTANDARD)": [],
#         "61-90 Days (SUBSTANDARD)": [],
#         "91-120 Days (DOUBTFUL)": [],
#         "121-180 Days (DOUBTFUL)": [],
#         "181-365 Days (LOSS)": [],
#         "Over 365 Days (LOSS)": [],
#     }

#     grand_totals = {
#         "total_principal": Decimal("0.00"),
#         "total_principal_due": Decimal("0.00"),
#         "total_interest_due": Decimal("0.00"),
#         "total_penalty_due": Decimal("0.00"),
#         "total_outstanding_balance": Decimal("0.00"),
#         "total_paid": Decimal("0.00"),
#     }

#     disbursed_loans = Loan.objects.filter(
#         status__in=["overdue", "disbursed"],
#         disbursement_date__isnull=False,
#     ).select_related("borrower")

#     bucket_totals = {key: grand_totals.copy() for key in aging_buckets}

#     def compute_installment_based_days_overdue(loan, today):
#         disbursement_date = loan.disbursement_date
#         term_months = loan.loan_period_months

#         if not disbursement_date or not term_months:
#             if loan.due_date:
#                 days_overdue = max((today - loan.due_date).days, 0)
#                 return days_overdue, None, loan.due_date
#             return 0, None, None

#         final_due_date = disbursement_date + relativedelta(months=term_months)
#         months_elapsed = (today.year - disbursement_date.year) * 12 + (today.month - disbursement_date.month)
#         if months_elapsed <= 0:
#             next_due = disbursement_date + relativedelta(months=1)
#             return 0, next_due, final_due_date

#         installments_due_by_now = min(months_elapsed, term_months)
#         total_principal_paid = loan.repayments.aggregate(total=Sum("principal_payment"))["total"] or Decimal("0.00")
#         scheduled_principal = (loan.principal_amount / Decimal(term_months)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
#         installments_paid = int(total_principal_paid / scheduled_principal)
#         next_unpaid_installment = installments_paid + 1

#         if next_unpaid_installment > term_months:
#             return 0, None, final_due_date

#         next_due_date = disbursement_date + relativedelta(months=next_unpaid_installment)
#         days_overdue = max((today - next_due_date).days, 0)
#         return days_overdue, next_due_date, final_due_date

#     for loan in disbursed_loans:
#         try:
#             remaining_balances = loan.calculate_remaining_balances()
#             remaining_principal = remaining_balances["principal_balance"]
#             remaining_interest = remaining_balances["interest_balance"]
#             penalty_balance = remaining_balances["penalty_balance"]
#             outstanding_balance = remaining_principal + remaining_interest + penalty_balance

#             if outstanding_balance <= 0:
#                 continue

#             days_overdue, next_due_date, final_due_date = compute_installment_based_days_overdue(loan, today)

#             total_paid = loan.repayments.aggregate(
#                 principal=Sum("principal_payment"),
#                 interest=Sum("interest_payment"),
#             )
#             total_paid_amount = (total_paid["principal"] or 0) + (total_paid["interest"] or 0)

#             loan_info = {
#                 "loan_id": loan.id,
#                 "borrower": loan.borrower.full_name,
#                 "principal_amount": loan.principal_amount,
#                 "interest_rate": loan.interest_rate,
#                 "loan_period_months": loan.loan_period_months,
#                 "start_date": loan.disbursement_date,
#                 "next_due_date": next_due_date,
#                 "due_date": final_due_date,
#                 "days_overdue": days_overdue,
#                 "principal_due": remaining_principal,
#                 "interest_due": remaining_interest,
#                 "penalty_due": penalty_balance,
#                 "outstanding_balance": outstanding_balance,
#                 "total_paid": total_paid_amount,
#             }

#             # Bucket assignment - COMBINED 0-30 days
#             if days_overdue <= 30:
#                 bucket_key = "0-30 Days (Performing / Watch)"
#             elif days_overdue <= 60:
#                 bucket_key = "31-60 Days (SUBSTANDARD)"
#             elif days_overdue <= 90:
#                 bucket_key = "61-90 Days (SUBSTANDARD)"
#             elif days_overdue <= 120:
#                 bucket_key = "91-120 Days (DOUBTFUL)"
#             elif days_overdue <= 180:
#                 bucket_key = "121-180 Days (DOUBTFUL)"
#             elif days_overdue <= 365:
#                 bucket_key = "181-365 Days (LOSS)"
#             else:
#                 bucket_key = "Over 365 Days (LOSS)"

#             aging_buckets[bucket_key].append(loan_info)

#             # Update bucket totals
#             bt = bucket_totals[bucket_key]
#             bt["total_principal"] += loan.principal_amount
#             bt["total_principal_due"] += remaining_principal
#             bt["total_interest_due"] += remaining_interest
#             bt["total_penalty_due"] += penalty_balance
#             bt["total_outstanding_balance"] += outstanding_balance
#             bt["total_paid"] += total_paid_amount

#         except Exception as e:
#             logger.error(f"Error processing loan {loan.id}: {e}")
#             continue

#     # Sort loans in each bucket by days_overdue (ascending)
#     for bucket_key in aging_buckets:
#         aging_buckets[bucket_key].sort(key=lambda x: x["days_overdue"])

#     # Compute grand totals
#     for bucket in bucket_totals.values():
#         for key in grand_totals:
#             grand_totals[key] += bucket[key]

#     fmt = lambda val: f"{float(val):,.0f}"

#     formatted_bucket_totals = {
#         key: {
#             "total_principal": fmt(bucket_totals[key]["total_principal"]),
#             "total_principal_due": fmt(bucket_totals[key]["total_principal_due"]),
#             "total_interest_due": fmt(bucket_totals[key]["total_interest_due"]),
#             "total_penalty_due": fmt(bucket_totals[key]["total_penalty_due"]),
#             "total_outstanding_balance": fmt(bucket_totals[key]["total_outstanding_balance"]),
#             "total_paid": fmt(bucket_totals[key]["total_paid"]),
#         }
#         for key in aging_buckets
#     }

#     formatted_grand_totals = {k: fmt(v) for k, v in grand_totals.items()}

#     bucket_data = [
#         {
#             'key': bucket_key,
#             'loans': aging_buckets[bucket_key],
#             'totals': formatted_bucket_totals[bucket_key],
#         }
#         for bucket_key in aging_buckets  # maintains order
#     ]

#     return render(
#         request,
#         "loans/loan_aging_report.html",
#         {
#             "bucket_data": bucket_data,
#             "formatted_grand_totals": formatted_grand_totals,
#             "bucket_totals": bucket_totals,
#             "grand_totals": grand_totals,
#             "table_title": "Loan Aging Report",
#             "total_loans": sum(len(loans) for loans in aging_buckets.values()),
#             "now": timezone.now(),
#         },
#     )


@login_required
@admin_or_manager_or_staff_required
def loan_aging_report(request):
    today = timezone.now().date()

    # NEW: Split 0-30 into two separate buckets
    aging_buckets = {
        "Current 0-Days (Performing)": [],
        "1-30 Days (Watch)": [],
        "31-60 Days (SUBSTANDARD)": [],
        "61-90 Days (SUBSTANDARD)": [],
        "91-120 Days (DOUBTFUL)": [],
        "121-180 Days (DOUBTFUL)": [],
        "181-365 Days (LOSS)": [],
        "Over 365 Days (LOSS)": [],
    }

    grand_totals = {
        "total_principal": Decimal("0.00"),
        "total_principal_due": Decimal("0.00"),
        "total_interest_due": Decimal("0.00"),
        "total_penalty_due": Decimal("0.00"),
        "total_outstanding_balance": Decimal("0.00"),
        "total_paid": Decimal("0.00"),
    }

    disbursed_loans = Loan.objects.filter(
        status__in=["overdue", "disbursed"],
        disbursement_date__isnull=False,
    ).select_related("borrower")

    bucket_totals = {key: grand_totals.copy() for key in aging_buckets}

    def compute_installment_based_days_overdue(loan, today):
        disbursement_date = loan.disbursement_date
        term_months = loan.loan_period_months

        if not disbursement_date or not term_months:
            if loan.due_date:
                days_overdue = max((today - loan.due_date).days, 0)
                return days_overdue, None, loan.due_date
            return 0, None, None

        final_due_date = disbursement_date + relativedelta(months=term_months)
        months_elapsed = (today.year - disbursement_date.year) * 12 + (
            today.month - disbursement_date.month
        )
        if months_elapsed <= 0:
            next_due = disbursement_date + relativedelta(months=1)
            return 0, next_due, final_due_date

        installments_due_by_now = min(months_elapsed, term_months)
        total_principal_paid = loan.repayments.aggregate(
            total=Sum("principal_payment")
        )["total"] or Decimal("0.00")
        scheduled_principal = (loan.principal_amount / Decimal(term_months)).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        installments_paid = int(total_principal_paid / scheduled_principal)
        next_unpaid_installment = installments_paid + 1

        if next_unpaid_installment > term_months:
            return 0, None, final_due_date

        next_due_date = disbursement_date + relativedelta(
            months=next_unpaid_installment
        )
        days_overdue = max((today - next_due_date).days, 0)
        return days_overdue, next_due_date, final_due_date

    for loan in disbursed_loans:
        try:
            remaining_balances = loan.calculate_remaining_balances()
            remaining_principal = remaining_balances["principal_balance"]
            remaining_interest = remaining_balances["interest_balance"]
            penalty_balance = remaining_balances["penalty_balance"]
            outstanding_balance = (
                remaining_principal + remaining_interest + penalty_balance
            )

            if outstanding_balance <= 0:
                continue

            days_overdue, next_due_date, final_due_date = (
                compute_installment_based_days_overdue(loan, today)
            )

            total_paid = loan.repayments.aggregate(
                principal=Sum("principal_payment"),
                interest=Sum("interest_payment"),
            )
            total_paid_amount = (total_paid["principal"] or 0) + (
                total_paid["interest"] or 0
            )

            loan_info = {
                "loan_id": loan.id,
                "borrower": loan.borrower.full_name,
                "principal_amount": loan.principal_amount,
                "interest_rate": loan.interest_rate,
                "loan_period_months": loan.loan_period_months,
                "start_date": loan.disbursement_date,
                "next_due_date": next_due_date,
                "due_date": final_due_date,
                "days_overdue": days_overdue,
                "principal_due": remaining_principal,
                "interest_due": remaining_interest,
                "penalty_due": penalty_balance,
                "outstanding_balance": outstanding_balance,
                "total_paid": total_paid_amount,
            }

            # NEW bucket logic – split 0-days and 1–30 days
            if days_overdue == 0:
                bucket_key = "Current 0-Days (Performing)"
            elif 1 <= days_overdue <= 30:
                bucket_key = "1-30 Days (Watch)"
            elif days_overdue <= 60:
                bucket_key = "31-60 Days (SUBSTANDARD)"
            elif days_overdue <= 90:
                bucket_key = "61-90 Days (SUBSTANDARD)"
            elif days_overdue <= 120:
                bucket_key = "91-120 Days (DOUBTFUL)"
            elif days_overdue <= 180:
                bucket_key = "121-180 Days (DOUBTFUL)"
            elif days_overdue <= 365:
                bucket_key = "181-365 Days (LOSS)"
            else:
                bucket_key = "Over 365 Days (LOSS)"

            aging_buckets[bucket_key].append(loan_info)

            # Update bucket totals
            bt = bucket_totals[bucket_key]
            bt["total_principal"] += loan.principal_amount
            bt["total_principal_due"] += remaining_principal
            bt["total_interest_due"] += remaining_interest
            bt["total_penalty_due"] += penalty_balance
            bt["total_outstanding_balance"] += outstanding_balance
            bt["total_paid"] += total_paid_amount

        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    # Sort loans in each bucket by days_overdue (ascending)
    for bucket_key in aging_buckets:
        aging_buckets[bucket_key].sort(key=lambda x: x["days_overdue"])

    # Compute grand totals
    for bucket in bucket_totals.values():
        for key in grand_totals:
            grand_totals[key] += bucket[key]

    fmt = lambda val: f"{float(val):,.0f}"

    formatted_bucket_totals = {
        key: {
            "total_principal": fmt(bucket_totals[key]["total_principal"]),
            "total_principal_due": fmt(bucket_totals[key]["total_principal_due"]),
            "total_interest_due": fmt(bucket_totals[key]["total_interest_due"]),
            "total_penalty_due": fmt(bucket_totals[key]["total_penalty_due"]),
            "total_outstanding_balance": fmt(
                bucket_totals[key]["total_outstanding_balance"]
            ),
            "total_paid": fmt(bucket_totals[key]["total_paid"]),
        }
        for key in aging_buckets
    }

    formatted_grand_totals = {k: fmt(v) for k, v in grand_totals.items()}

    bucket_data = [
        {
            "key": bucket_key,
            "loans": aging_buckets[bucket_key],
            "totals": formatted_bucket_totals[bucket_key],
        }
        for bucket_key in aging_buckets  # preserves insertion order
    ]

    return render(
        request,
        "loans/loan_aging_report.html",
        {
            "bucket_data": bucket_data,
            "formatted_grand_totals": formatted_grand_totals,
            "bucket_totals": bucket_totals,
            "grand_totals": grand_totals,
            "table_title": "Loan Aging Report",
            "total_loans": sum(len(loans) for loans in aging_buckets.values()),
            "now": timezone.now(),
        },
    )


# =================================== Loan Arrears Report view ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_arrears_report(request):
    today = timezone.now().date()

    # === ARREARS BUCKETS (Only past due loans) ===
    arrears_buckets = {
        "1-30 Days (WATCH)": [],
        "31-60 Days (SUBSTANDARD)": [],
        "61-90 Days (SUBSTANDARD)": [],
        "91-120 Days (DOUBTFUL)": [],
        "121-180 Days (DOUBTFUL)": [],
        "181-365 Days (LOSS)": [],
        "Over 365 Days (LOSS)": [],
    }

    # Totals per bucket
    bucket_totals = {
        key: {
            "loan_count": 0,
            "total_principal": Decimal("0.00"),
            "total_principal_due": Decimal("0.00"),
            "total_interest_due": Decimal("0.00"),
            "total_outstanding": Decimal("0.00"),
        }
        for key in arrears_buckets
    }

    grand_totals = {
        "loan_count": 0,
        "total_principal": Decimal("0.00"),
        "total_principal_due": Decimal("0.00"),
        "total_interest_due": Decimal("0.00"),
        "total_outstanding": Decimal("0.00"),
    }

    # Fetch only active loans
    loans = Loan.objects.filter(
        status__in=["disbursed", "overdue"], disbursement_date__isnull=False
    ).select_related("borrower")

    # === Helper: Compute days overdue based on installments ===
    def compute_days_overdue(loan: Loan, today: date):
        disbursement_date = loan.disbursement_date
        term_months = loan.loan_period_months or 0

        if not disbursement_date or term_months == 0:
            if loan.due_date:
                return max((today - loan.due_date).days, 0), loan.due_date
            return 0, None

        final_due_date = disbursement_date + relativedelta(months=term_months)

        # Principal paid so far
        paid = loan.repayments.aggregate(p=Sum("principal_payment"))["p"] or Decimal(
            "0"
        )
        per_installment = (loan.principal_amount / Decimal(term_months)).quantize(
            Decimal("0.01"), rounding="ROUND_DOWN"
        )
        installments_paid = int(paid / per_installment) if per_installment > 0 else 0
        next_installment_num = installments_paid + 1

        if next_installment_num > term_months:
            return 0, final_due_date  # Fully paid

        next_due_date = disbursement_date + relativedelta(months=next_installment_num)
        days_overdue = max((today - next_due_date).days, 0)
        return days_overdue, next_due_date

    # === Process Each Loan ===
    for loan in loans:
        try:
            balances = loan.calculate_remaining_balances()
            principal_due = balances["principal_balance"]
            interest_due = balances["interest_balance"]
            penalty_due = balances.get("penalty_balance", Decimal("0"))
            outstanding = principal_due + interest_due + penalty_due

            if outstanding <= 0:
                continue

            days_overdue, next_due = compute_days_overdue(loan, today)

            # CRITICAL: Skip current loans
            if days_overdue == 0:
                continue

            # Determine bucket
            if days_overdue <= 30:
                bucket = "1-30 Days (WATCH)"
            elif days_overdue <= 60:
                bucket = "31-60 Days (SUBSTANDARD)"
            elif days_overdue <= 90:
                bucket = "61-90 Days (SUBSTANDARD)"
            elif days_overdue <= 120:
                bucket = "91-120 Days (DOUBTFUL)"
            elif days_overdue <= 180:
                bucket = "121-180 Days (DOUBTFUL)"
            elif days_overdue <= 365:
                bucket = "181-365 Days (LOSS)"
            else:
                bucket = "Over 365 Days (LOSS)"

            loan_info = {
                "loan_id": loan.id,
                "borrower": loan.borrower.full_name,
                "principal_amount": loan.principal_amount,
                "interest_rate": loan.interest_rate,
                "term_months": loan.loan_period_months,
                "disbursement_date": loan.disbursement_date,
                "final_due_date": (
                    loan.disbursement_date
                    + relativedelta(months=loan.loan_period_months)
                    if loan.loan_period_months
                    else None
                ),
                "next_due_date": next_due,
                "days_overdue": days_overdue,
                "principal_due": principal_due,
                "interest_due": interest_due,
                "outstanding": outstanding,
            }

            arrears_buckets[bucket].append(loan_info)
            bt = bucket_totals[bucket]
            bt["loan_count"] += 1
            bt["total_principal"] += loan.principal_amount
            bt["total_principal_due"] += principal_due
            bt["total_interest_due"] += interest_due
            bt["total_outstanding"] += outstanding

        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}")
            continue

    # === Sort each bucket: Worst first ===
    for bucket in arrears_buckets:
        arrears_buckets[bucket].sort(
            key=lambda x: (-x["days_overdue"], -float(x["outstanding"]))
        )

    # === Aggregate grand totals ===
    for bt in bucket_totals.values():
        for key in grand_totals:
            grand_totals[key] += bt[key]

    # === Formatting helper ===
    fmt = lambda x: f"{float(x):,.0f}"

    # Prepare data for template
    bucket_data = []
    for key in arrears_buckets:
        bucket_data.append(
            {
                "name": key,
                "loans": arrears_buckets[key],
                "count": bucket_totals[key]["loan_count"],
                "totals": {
                    "principal": fmt(bucket_totals[key]["total_principal"]),
                    "principal_due": fmt(bucket_totals[key]["total_principal_due"]),
                    "interest_due": fmt(bucket_totals[key]["total_interest_due"]),
                    "outstanding": fmt(bucket_totals[key]["total_outstanding"]),
                },
            }
        )

    context = {
        "bucket_data": bucket_data,
        "grand_totals": {
            "count": grand_totals["loan_count"],
            "principal": fmt(grand_totals["total_principal"]),
            "principal_due": fmt(grand_totals["total_principal_due"]),
            "interest_due": fmt(grand_totals["total_interest_due"]),
            "outstanding": fmt(grand_totals["total_outstanding"]),
        },
        "report_date": today.strftime("%d %B %Y"),
        "title": "Loan Arrears Report (Past Due Only)",
    }

    return render(request, "loans/loan_arrears_report.html", context)


# =================================== loan_portfolio_report view ===================================
@login_required
@admin_or_manager_or_staff_required
def loan_portfolio_report(request):
    today = timezone.now().date()

    # Fetch loans with borrower
    loans = Loan.objects.select_related("borrower").prefetch_related("repayments").all()

    loan_data = []
    total_principal = Decimal("0.00")
    total_remaining_principal = Decimal("0.00")
    total_remaining_interest = Decimal("0.00")
    total_penalty_balance = Decimal("0.00")
    total_remaining_balance = Decimal("0.00")

    for loan in loans:
        try:
            # Remaining balances
            balances = loan.calculate_remaining_balances()
            remaining_principal = balances["principal_balance"]
            remaining_interest = balances["interest_balance"]
            penalty_balance = balances["penalty_balance"]
            total_balance = remaining_principal + remaining_interest + penalty_balance

            # Skip fully paid loans
            if total_balance <= 0:
                continue

            # Days overdue
            days_overdue = (
                (today - loan.due_date).days
                if loan.due_date and loan.due_date < today
                else 0
            )

            # Last repayment
            last_repayment = loan.repayments.order_by("-repayment_date").first()
            last_payment_date = (
                last_repayment.repayment_date if last_repayment else None
            )

            # Next payment using installment-based calculation
            def get_next_payment_date(loan):
                if not loan.disbursement_date:
                    return None
                term_months = loan.loan_period_months
                total_principal_paid = loan.repayments.aggregate(
                    total=Sum("principal_payment")
                )["total"] or Decimal("0.00")
                scheduled_principal = (loan.principal_amount / term_months).quantize(
                    Decimal("0.01")
                )
                installments_paid = int(total_principal_paid / scheduled_principal)
                next_unpaid = installments_paid + 1
                if next_unpaid > term_months:
                    return None
                return loan.disbursement_date + relativedelta(months=next_unpaid)

            next_payment_date = get_next_payment_date(loan)

            # Sum totals
            total_principal += loan.principal_amount
            total_remaining_principal += remaining_principal
            total_remaining_interest += remaining_interest
            total_penalty_balance += penalty_balance
            total_remaining_balance += total_balance

            loan_data.append(
                {
                    "loan_id": loan.id,
                    "borrower": loan.borrower.full_name,
                    "principal_amount": loan.principal_amount,
                    "interest_rate": loan.interest_rate,
                    "loan_period_months": loan.loan_period_months,
                    "remaining_principal": remaining_principal,
                    "remaining_interest": remaining_interest,
                    "penalty_balance": penalty_balance,
                    "total_remaining_balance": total_balance,
                    "disbursement_date": loan.disbursement_date,
                    "due_date": loan.due_date,
                    "days_overdue": days_overdue,
                    "last_payment": last_payment_date,
                    "next_payment": next_payment_date,
                }
            )

        except Exception as e:
            logger.error(f"Error processing loan {loan.id}: {e}", exc_info=True)
            continue

    # Sort by disbursement_date
    loan_data = sorted(
        loan_data, key=lambda x: x["disbursement_date"] or timezone.datetime.min
    )

    # Pagination
    paginator = Paginator(loan_data, 50)
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
def portfolio_at_risk(request):
    today = timezone.now().date()

    # Active loans only
    loans = Loan.objects.filter(
        status__in=["disbursed", "overdue"], disbursement_date__isnull=False
    ).select_related("borrower")

    # PAR Buckets (outstanding balance in each category)
    par = {
        "par_1": Decimal("0.00"),  # 1+ days
        "par_30": Decimal("0.00"),
        "par_60": Decimal("0.00"),
        "par_90": Decimal("0.00"),
        "par_120": Decimal("0.00"),
        "par_180": Decimal("0.00"),
    }

    total_portfolio = Decimal("0.00")
    total_loans_count = 0

    # Helper: Accurate days overdue (installment-based)
    def get_days_overdue(loan):
        if not loan.disbursement_date or not loan.loan_period_months:
            return (
                max((today - (loan.due_date or today)).days, 0) if loan.due_date else 0
            )

        paid_principal = loan.repayments.aggregate(p=Sum("principal_payment"))[
            "p"
        ] or Decimal("0")
        per_month = (loan.principal_amount / Decimal(loan.loan_period_months)).quantize(
            Decimal("0.01")
        )
        paid_installments = int(paid_principal / per_month) if per_month > 0 else 0
        next_installment = paid_installments + 1

        if next_installment > loan.loan_period_months:
            return 0

        next_due = loan.disbursement_date + relativedelta(months=next_installment)
        return max((today - next_due).days, 0)

    for loan in loans:
        balances = loan.calculate_remaining_balances()
        outstanding = (
            balances["principal_balance"]
            + balances["interest_balance"]
            + balances.get("penalty_balance", Decimal("0"))
        )

        if outstanding <= 0:
            continue

        total_portfolio += outstanding
        total_loans_count += 1

        days = get_days_overdue(loan)

        if days >= 1:
            par["par_1"] += outstanding
        if days >= 30:
            par["par_30"] += outstanding
        if days >= 60:
            par["par_60"] += outstanding
        if days >= 90:
            par["par_90"] += outstanding
        if days >= 120:
            par["par_120"] += outstanding
        if days >= 180:
            par["par_180"] += outstanding

    # Calculate percentages
    def pct(val):
        return (val / total_portfolio * 100) if total_portfolio > 0 else Decimal("0.00")

    context = {
        "total_portfolio": total_portfolio,
        "total_loans": total_loans_count,
        "par": {
            "par_1_amount": par["par_1"],
            "par_1_pct": pct(par["par_1"]),
            "par_30_amount": par["par_30"],
            "par_30_pct": pct(par["par_30"]),
            "par_60_amount": par["par_60"],
            "par_60_pct": pct(par["par_60"]),
            "par_90_amount": par["par_90"],
            "par_90_pct": pct(par["par_90"]),
            "par_120_amount": par["par_120"],
            "par_120_pct": pct(par["par_120"]),
            "par_180_amount": par["par_180"],
            "par_180_pct": pct(par["par_180"]),
        },
        "report_date": today.strftime("%d %B %Y"),
        "title": "Portfolio at Risk (PAR) Summary Report",
    }

    return render(request, "loans/portfolio_at_risk_report.html", context)


# =================================== non_performing_loans view ===================================
@login_required
@admin_or_manager_or_staff_required
def non_performing_loans(request):
    today = timezone.now().date()

    # Fetch potentially non-performing loans
    loans_qs = (
        Loan.objects.filter(
            Q(status="overdue")
            | Q(due_date__lt=today, status__in=["disbursed", "approved"])
        )
        .select_related("borrower", "account")
        .prefetch_related("repayments")
    )

    loan_data = []

    for loan in loans_qs:
        balances = loan.calculate_remaining_balances()
        outstanding_balance = (
            balances["principal_balance"]
            + balances["interest_balance"]
            + balances["penalty_balance"]
        )

        if outstanding_balance <= 0:
            continue

        # Last repayment
        last_repayment = loan.repayments.order_by("-repayment_date").first()
        last_payment_date = last_repayment.repayment_date if last_repayment else None

        # Next expected payment (installment-based)
        def get_next_payment_date(loan):
            if not loan.disbursement_date or not loan.loan_period_months:
                return None
            term_months = loan.loan_period_months
            total_principal_paid = loan.repayments.aggregate(
                total=Sum("principal_payment")
            )["total"] or Decimal("0.00")
            scheduled_principal = (loan.principal_amount / term_months).quantize(
                Decimal("0.01")
            )
            installments_paid = int(total_principal_paid / scheduled_principal)
            next_unpaid = installments_paid + 1
            if next_unpaid > term_months:
                return None
            return loan.disbursement_date + relativedelta(months=next_unpaid)

        next_payment_date = get_next_payment_date(loan)

        # Days overdue
        days_overdue = (
            max((today - loan.due_date).days, 0)
            if loan.due_date and loan.due_date < today
            else 0
        )

        loan_data.append(
            {
                "loan_id": loan.id,
                "borrower": loan.borrower.full_name,
                "principal_amount": loan.principal_amount,
                "interest_rate": loan.interest_rate,
                "status": loan.status,
                "due_date": loan.due_date,
                "days_overdue": days_overdue,
                "outstanding_balance": outstanding_balance,
                "last_payment": last_payment_date,
                "next_payment": next_payment_date,
            }
        )

    # Sort by days overdue descending
    loan_data.sort(key=lambda x: x["days_overdue"], reverse=True)

    # Pagination
    paginator = Paginator(loan_data, 50)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        "page_obj": page_obj,
        "table_title": "Non-Performing Loans with Outstanding Balance",
        "today": today,
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
# @login_required
# @admin_or_manager_or_staff_required
# def loan_due_overdue_report(request):
#     try:
#         timezone.activate(pytz.timezone("Africa/Nairobi"))
#     except:
#         timezone.activate(pytz.UTC)

#     # Selected date
#     selected_date_str = request.GET.get("selected_date")
#     selected_date = (
#         datetime.strptime(selected_date_str, "%Y-%m-%d").date()
#         if selected_date_str
#         else timezone.now().date()
#     )

#     # Search & Pagination
#     search_term = request.GET.get("search", "").strip().lower()
#     page_due = request.GET.get("page_due", 1)
#     page_overdue = request.GET.get("page_overdue", 1)
#     page_arrears = request.GET.get("page_arrears", 1)

#     cache_key = f"due_overdue_report_{selected_date}_{search_term}_{page_due}_{page_overdue}_{page_arrears}"
#     if not search_term:
#         cached = cache.get(cache_key)
#         if cached:
#             return render(request, "loans/loan_overdue_report.html", cached)

#     loans_qs = (
#         Loan.objects.filter(status__in=["disbursed", "overdue"])
#         .select_related("borrower")
#         .prefetch_related("repayments", "penalties")
#         .order_by("id")
#     )

#     due_loans_list = []
#     overdue_loans_list = []  # ← Only past maturity
#     arrears_loans_list = []  # ← Missed instalments, maturity in future

#     for loan in loans_qs:
#         try:
#             if not loan.disbursement_date or loan.loan_period_months <= 0:
#                 continue

#             # Safe search filter
#             if search_term:
#                 borrower = loan.borrower
#                 phone = getattr(borrower, "phone_number", "") or ""
#                 searchable = f"{loan.id} {getattr(borrower, 'full_name', '')} {phone} {loan.principal_amount}".lower()
#                 if search_term not in searchable:
#                     continue

#             balances = loan.calculate_remaining_balances()
#             total_balance = sum(balances.values())
#             if total_balance <= 0:
#                 continue

#             schedule = loan.generate_payment_schedule() or []
#             payments = [
#                 {
#                     **p,
#                     "payment_due_date": (
#                         p["payment_due_date"].date()
#                         if hasattr(p["payment_due_date"], "date")
#                         else p["payment_due_date"]
#                     ),
#                 }
#                 for p in schedule
#                 if p.get("principal_payment", 0) + p.get("interest_payment", 0) > 0
#             ]

#             # 1. FULLY OVERDUE: Maturity date passed
#             if loan.due_date and loan.due_date < selected_date:
#                 days_overdue = (selected_date - loan.due_date).days
#                 due_balance = min(
#                     loan.calculate_total_amount_due_balance(
#                         due_date=selected_date, total_amount_due=total_balance
#                     ),
#                     total_balance,
#                 )
#                 if due_balance > 0:
#                     overdue_loans_list.append(
#                         {
#                             "loan": loan,
#                             "principal_balance": balances["principal_balance"],
#                             "interest_balance": balances["interest_balance"],
#                             "penalty_balance": balances["penalty_balance"],
#                             "total_balance": total_balance,
#                             "disbursement_date": loan.disbursement_date,
#                             "maturity_due_date": loan.due_date,
#                             "total_amount_due_balance": due_balance,
#                             "days_overdue": days_overdue,
#                         }
#                     )
#                 continue  # Skip rest

#             # 2. LOANS IN ARREARS: Missed instalments
#             missed = [p for p in payments if p["payment_due_date"] < selected_date]
#             if missed:
#                 earliest = min(p["payment_due_date"] for p in missed)
#                 days_arrears = (selected_date - earliest).days
#                 expected = sum(
#                     p["principal_payment"] + p["interest_payment"] for p in missed
#                 )
#                 due_balance = min(
#                     loan.calculate_total_amount_due_balance(
#                         due_date=selected_date, total_amount_due=Decimal(expected)
#                     ),
#                     total_balance,
#                 )
#                 if due_balance > 0:
#                     arrears_loans_list.append(
#                         {
#                             "loan": loan,
#                             "principal_balance": balances["principal_balance"],
#                             "interest_balance": balances["interest_balance"],
#                             "penalty_balance": balances["penalty_balance"],
#                             "total_balance": total_balance,
#                             "disbursement_date": loan.disbursement_date,
#                             "maturity_due_date": loan.due_date,
#                             "total_amount_due_balance": due_balance,
#                             "days_overdue": days_arrears,
#                         }
#                     )

#             # 3. DUE TODAY
#             due_today = [p for p in payments if p["payment_due_date"] == selected_date]
#             if due_today or (loan.due_date == selected_date):
#                 expected = (
#                     sum(
#                         p["principal_payment"] + p["interest_payment"]
#                         for p in due_today
#                     )
#                     if due_today
#                     else total_balance
#                 )
#                 due_balance = min(
#                     loan.calculate_total_amount_due_balance(
#                         due_date=selected_date, total_amount_due=Decimal(expected)
#                     ),
#                     total_balance,
#                 )
#                 if due_balance > 0:
#                     due_loans_list.append(
#                         {
#                             "loan": loan,
#                             "principal_balance": balances["principal_balance"],
#                             "interest_balance": balances["interest_balance"],
#                             "penalty_balance": balances["penalty_balance"],
#                             "total_balance": total_balance,
#                             "disbursement_date": loan.disbursement_date,
#                             "maturity_due_date": loan.due_date,
#                             "total_amount_due_balance": due_balance,
#                         }
#                     )

#         except Exception as e:
#             logger.error(f"Error processing loan {loan.id}: {e}")
#             continue

#     # Pagination
#     if search_term:
#         due_loans = due_loans_list
#         overdue_loans = overdue_loans_list
#         arrears_loans = arrears_loans_list
#     else:
#         due_loans = Paginator(due_loans_list, 50).get_page(page_due)
#         overdue_loans = Paginator(overdue_loans_list, 50).get_page(page_overdue)
#         arrears_loans = Paginator(arrears_loans_list, 50).get_page(page_arrears)

#     context = {
#         "due_loans": due_loans,
#         "overdue_loans": overdue_loans,
#         "arrears_loans": arrears_loans,
#         "due_loans_total_balance": sum(i["total_balance"] for i in due_loans_list),
#         "overdue_loans_total_balance": sum(
#             i["total_balance"] for i in overdue_loans_list
#         ),
#         "arrears_loans_total_balance": sum(
#             i["total_balance"] for i in arrears_loans_list
#         ),
#         "due_loans_count": len(due_loans_list),
#         "overdue_loans_count": len(overdue_loans_list),
#         "arrears_loans_count": len(arrears_loans_list),
#         "selected_date": selected_date,
#         "now": timezone.now(),
#         "table_title": "Due, Arrears & Overdue Loans Report",
#     }

#     if not search_term:
#         cache.set(cache_key, context, 3600)

#     return render(request, "loans/loan_overdue_report.html", context)

@login_required
@admin_or_manager_or_staff_required
def loan_due_overdue_report(request):
    try:
        timezone.activate(pytz.timezone("Africa/Nairobi"))
    except:
        timezone.activate(pytz.UTC)

    selected_date_str = request.GET.get("selected_date")
    selected_date = (
        datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date_str
        else timezone.now().date()
    )

    search_term = request.GET.get("search", "").strip().lower()
    page_due = int(request.GET.get("page_due", 1))
    page_arrears = int(request.GET.get("page_arrears", 1))
    page_overdue = int(request.GET.get("page_overdue", 1))

    cache_key = f"due_overdue_report_{selected_date}_{search_term}_{page_due}_{page_arrears}_{page_overdue}"
    if not search_term:
        cached = cache.get(cache_key)
        if cached:
            return render(request, "loans/loan_overdue_report.html", cached)

    loans_qs = (
        Loan.objects.filter(status__in=["disbursed", "overdue"])
        .select_related("borrower")
        .prefetch_related("repayments", "penalties")
        .order_by("id")
    )

    due_today_list = []
    arrears_list = []
    past_maturity_list = []

    for loan in loans_qs:
        try:
            if not loan.disbursement_date or loan.loan_period_months <= 0:
                continue

            # Search filter
            if search_term:
                borrower = loan.borrower
                searchable = " ".join([
                    str(loan.id).lower(),
                    borrower.full_name.lower() if hasattr(borrower, 'full_name') else "",
                    getattr(borrower, 'phone_number', '').lower(),
                    str(loan.principal_amount),
                ])
                if search_term not in searchable:
                    continue

            balances = loan.calculate_remaining_balances()
            total_outstanding = sum(balances.values())
            if total_outstanding <= 0:
                continue

            schedule = loan.generate_payment_schedule() or []
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
                if p.get("principal_payment", 0) + p.get("interest_payment", 0) > 0
            ]

            # DUE TODAY
            due_today_payments = [p for p in payments if p["payment_due_date"] == selected_date]
            if due_today_payments:
                expected = sum(p["principal_payment"] + p["interest_payment"] for p in due_today_payments)
                due_amount = loan.calculate_total_amount_due_balance(selected_date, Decimal(expected))
                if due_amount > 0:
                    due_today_list.append({
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_outstanding": total_outstanding,
                        "due_amount": due_amount,
                    })
                continue

            # ARREARS (missed installments + maturity not yet passed)
            missed = [p for p in payments if p["payment_due_date"] < selected_date]
            if missed and (not loan.due_date or loan.due_date >= selected_date):
                earliest = min(p["payment_due_date"] for p in missed)
                days_arrears = (selected_date - earliest).days
                expected_arrears = sum(p["principal_payment"] + p["interest_payment"] for p in missed)
                arrears_amount = loan.calculate_total_amount_due_balance(selected_date, Decimal(expected_arrears))
                if arrears_amount > 0:
                    arrears_list.append({
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_outstanding": total_outstanding,
                        "arrears_amount": arrears_amount,
                        "days_arrears": days_arrears,
                    })

            # PAST MATURITY OVERDUE
            if loan.due_date and loan.due_date < selected_date:
                days_past_maturity = (selected_date - loan.due_date).days
                maturity_amount = loan.calculate_total_amount_due_balance(selected_date, total_outstanding)
                if maturity_amount > 0:
                    past_maturity_list.append({
                        "loan": loan,
                        "principal_balance": balances["principal_balance"],
                        "interest_balance": balances["interest_balance"],
                        "penalty_balance": balances["penalty_balance"],
                        "total_outstanding": total_outstanding,
                        "maturity_amount": maturity_amount,
                        "days_past_maturity": days_past_maturity,
                    })

        except Exception as e:
            logger.error(f"Loan {loan.id} error: {e}")
            continue

    # Pagination
    per_page = 50
    due_page = Paginator(due_today_list, per_page).get_page(page_due)
    arrears_page = Paginator(arrears_list, per_page).get_page(page_arrears)
    overdue_page = Paginator(past_maturity_list, per_page).get_page(page_overdue)

    context = {
        "due_loans": due_page,
        "arrears_loans": arrears_page,
        "overdue_loans": overdue_page,

        "due_loans_count": len(due_today_list),
        "arrears_loans_count": len(arrears_list),
        "overdue_loans_count": len(past_maturity_list),

        "due_loans_total": sum(i["total_outstanding"] for i in due_today_list),
        "arrears_loans_total": sum(i["total_outstanding"] for i in arrears_list),
        "overdue_loans_total": sum(i["total_outstanding"] for i in past_maturity_list),

        "selected_date": selected_date,
        "now": timezone.now(),
        "table_title": "Due, Arrears & Past Maturity Loans Report",
    }

    if not search_term:
        cache.set(cache_key, context, 3600)

    return render(request, "loans/loan_overdue_report.html", context)

# =================================== loan_penalty_management view ===================================

@login_required
@admin_or_manager_or_staff_required
def loan_penalty_management(request):
    clients_with_loans = (
        Client.objects.filter(loans__isnull=False).distinct().order_by("full_name")
    )

    selected_client = None
    unpaid_penalties = []
    paid_penalties = []
    unpaid_total = paid_total = total_ever = Decimal("0.00")
    unpaid_count = paid_count = 0

    if request.method == "POST":
        client_id = request.POST.get("client_id")
        if client_id:
            selected_client = get_object_or_404(Client, id=client_id)

            # ---------------- UNPAID PENALTIES ----------------
            unpaid_penalties = (
                LoanPenalty.objects.filter(
                    loan__borrower=selected_client,
                    is_paid=False,
                    remaining_amount__gt=0,
                    is_deleted=False,
                )
                .select_related("loan")
                .order_by("-penalty_date")
            )

            unpaid_total = unpaid_penalties.aggregate(t=Sum("remaining_amount"))[
                "t"
            ] or Decimal("0")
            unpaid_count = unpaid_penalties.count()

            # ---------------- PAID PENALTIES ----------------
            penalty_repayments = (
                LoanRepayment.objects.filter(
                    loan__borrower=selected_client, penalty_payment__gt=0
                )
                .select_related("loan")
                .order_by("-repayment_date")
            )

            paid_penalty_ids = set()
            paid_penalties = []

            # Map repayments to penalties paid
            for repayment in penalty_repayments:
                recent_paid = LoanPenalty.objects.filter(
                    loan=repayment.loan,
                    is_paid=True,
                    updated_at__gte=repayment.repayment_date - timedelta(minutes=5),
                    updated_at__lte=repayment.repayment_date + timedelta(minutes=5),
                    is_deleted=False,
                )
                for penalty in recent_paid:
                    if penalty.id not in paid_penalty_ids:
                        paid_penalty_ids.add(penalty.id)
                        paid_penalties.append(
                            {
                                "penalty": penalty,
                                "paid_on": repayment.repayment_date,
                                "paid_via_repayment": repayment.id,
                            }
                        )

            # Include any remaining paid penalties
            remaining_paid = LoanPenalty.objects.filter(
                loan__borrower=selected_client, is_paid=True, is_deleted=False
            ).exclude(id__in=paid_penalty_ids)

            for penalty in remaining_paid:
                paid_penalties.append(
                    {
                        "penalty": penalty,
                        "paid_on": penalty.updated_at.date(),
                        "paid_via_repayment": None,
                    }
                )

            paid_total = sum(p["penalty"].penalty_amount for p in paid_penalties)
            paid_count = len(paid_penalties)
            total_ever = unpaid_total + paid_total

            # ---------------- HARD DELETE SELECTED PENALTIES ----------------
            if "delete_selected" in request.POST:
                penalty_ids = request.POST.getlist("penalty_ids")

                if penalty_ids:
                    penalties_to_delete = LoanPenalty.objects.filter(
                        id__in=penalty_ids,
                        loan__borrower=selected_client,
                    )

                    count = penalties_to_delete.count()

                    # Delete related transaction history first (optional but safer)
                    for penalty in penalties_to_delete:
                        TransactionHistory.objects.filter(
                            loan=penalty.loan,
                            description__icontains="Penalty",
                            amount=penalty.penalty_amount,
                        ).delete()

                    # Permanently delete penalties
                    penalties_to_delete.delete()                       

                    messages.success(
                        request,
                        f"Deleted {count} penalty{'y' if count == 1 else 'ies'} permanently.",
                    )

                    # Refresh lists
                    unpaid_penalties = unpaid_penalties.exclude(id__in=penalty_ids)
                    paid_penalties = [
                        p
                        for p in paid_penalties
                        if str(p["penalty"].id) not in penalty_ids
                    ]

    context = {
        "table_title": "Loan Penalties Management",
        "clients": clients_with_loans,
        "selected_client": selected_client,
        "unpaid_penalties": unpaid_penalties,
        "paid_penalties": paid_penalties,
        "unpaid_total": unpaid_total,
        "paid_total": paid_total,
        "total_ever": total_ever,
        "unpaid_count": unpaid_count,
        "paid_count": paid_count,
    }
    return render(request, "loans/loan_penalty_management.html", context)
