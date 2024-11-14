import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, FloatField, Sum
from django.db.models.functions import Coalesce, ExtractYear
from django.http import JsonResponse
from django.shortcuts import render

from apps.child.models import Child
from apps.finance.models import ChildPayments, StaffPayments
from apps.inventory.products.models import Category, Product
from apps.inventory.sales.models import Sale
from apps.loans.models import Loan, LoanRepayment
from apps.sponsor.models import Sponsor
from apps.sponsorship.models import ChildSponsorship, StaffSponsorship
from apps.users.decorators import admin_or_manager_or_staff_required

from .utils import (
    get_top_selling_products,
)


def home(request):
    return render(request, "accounts/home.html")


# =================================== The dashboard ===================================
@login_required
@admin_or_manager_or_staff_required
def dashboard(request):
    # Retrieve counts using annotations
    sponsors_count = Sponsor.objects.filter(is_departed=False).count()
    children_count = Child.objects.count()
    sponsored_count = ChildSponsorship.objects.filter(is_active=True).count()
    non_sponsored_count = Child.objects.filter(
        is_departed=False, is_sponsored=False
    ).count()
    children_departed_count = Child.objects.filter(is_departed=True).count()

    # Get top sponsors and children
    top_sponsors_data = get_top_sponsors()
    top_children_data = get_top_children_sponsored()
    top_staff_data = get_top_staff_sponsored()

    # Combine sponsors and counts into a list of tuples
    top_sponsors_with_counts = list(
        zip(top_sponsors_data["sponsors"], top_sponsors_data["counts"])
    )
    top_children_with_counts = list(
        zip(top_children_data["children"], top_children_data["counts"])
    )
    top_staff_with_counts = list(
        zip(top_staff_data["staff_active"], top_staff_data["counts"])
    )
    context = {
        "sponsors_count": sponsors_count,
        "children_count": children_count,
        "children_departed_count": children_departed_count,
        "sponsored_count": sponsored_count,
        "non_sponsored_count": non_sponsored_count,
        "top_sponsors_with_counts": top_sponsors_with_counts,
        "top_children_with_counts": top_children_with_counts,
        "top_staff_with_counts": top_staff_with_counts,
    }

    return render(request, "main/main_dashboard.html", context)


# =================================== Child Sponsorship Count ===================================
def get_top_sponsors():
    # Get the top sponsors with the most sponsored children
    top_sponsors = (
        ChildSponsorship.objects.values("sponsor__first_name", "sponsor__last_name")
        .annotate(total_sponsored=Count("child"))
        .order_by("-total_sponsored")[:5]
    )

    sponsors = [
        f"{sponsor['sponsor__first_name']} {sponsor['sponsor__last_name']}"
        for sponsor in top_sponsors
    ]
    counts = [sponsor["total_sponsored"] for sponsor in top_sponsors]

    return {
        "sponsors": sponsors,
        "counts": counts,
    }


def get_top_children_sponsored():
    # Get the top children with the most sponsors
    top_children = (
        ChildSponsorship.objects.values(
            "child__full_name"
        )  # Use the correct reference to child model
        .annotate(total_sponsors=Count("sponsor"))
        .order_by("-total_sponsors")[:5]
    )

    # Extract child names and sponsor counts
    children = [child["child__full_name"] for child in top_children]
    counts = [child["total_sponsors"] for child in top_children]

    return {
        "children": children,
        "counts": counts,
    }


def get_top_staff_sponsored():
    # Query to get the top staff with the most sponsors
    top_staff = (
        StaffSponsorship.objects.values("staff__first_name", "staff__last_name")
        .annotate(total_sponsors=Count("sponsor"))
        .order_by("-total_sponsors")[:5]
    )

    # Extract staff names and sponsor counts
    staff_active = [
        f"{staff['staff__first_name']} {staff['staff__last_name']}"
        for staff in top_staff
    ]
    counts = [staff["total_sponsors"] for staff in top_staff]

    return {
        "staff_active": staff_active,
        "counts": counts,
    }


# =================================== Sponsorship Chart ===================================


def sponsorship_chart(request):
    data = ChildSponsorship.objects.values("sponsorship_type").annotate(
        count=Count("sponsorship_type")
    )
    return JsonResponse(list(data), safe=False)


# =================================== Sponsors Graph ===================================
@login_required
@admin_or_manager_or_staff_required
def get_sponsors_data(request):
    try:
        sponsors_per_year = (
            Sponsor.objects.annotate(year=ExtractYear("start_date"))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

        data = list(sponsors_per_year)

        return JsonResponse(data, safe=False, status=200)

    except Sponsor.DoesNotExist:
        return JsonResponse({"error": "No sponsor data found"}, status=404)

    except Exception:
        # Log the exception here if logging is set up
        return JsonResponse(
            {"error": "An error occurred while fetching the data"}, status=500
        )


# =================================== Children Graph ===================================
@login_required
@admin_or_manager_or_staff_required
def get_children_data(request):
    try:
        children_per_year = (
            Child.objects.annotate(year=ExtractYear("registration_date"))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

        data = list(children_per_year)

        return JsonResponse(data, safe=False, status=200)

    except Child.DoesNotExist:
        return JsonResponse({"error": "No children data found"}, status=404)

    except Exception:
        # Log the exception here if logging is set up
        return JsonResponse(
            {"error": "An error occurred while fetching the data"}, status=500
        )


# =================================== Sponsors & Children ===================================
@login_required
@admin_or_manager_or_staff_required
def get_combined_data(request):
    try:
        sponsors_per_year = (
            Sponsor.objects.annotate(year=ExtractYear("start_date"))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )
        children_per_year = (
            Child.objects.annotate(year=ExtractYear("registration_date"))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

        sponsors_data = {item["year"]: item["count"] for item in sponsors_per_year}
        children_data = {item["year"]: item["count"] for item in children_per_year}

        combined_data = {
            "sponsors": sponsors_data,
            "children": children_data,
        }

        return JsonResponse(combined_data, safe=False, status=200)

    except Sponsor.DoesNotExist:
        return JsonResponse({"error": "No sponsor data found"}, status=404)

    except Child.DoesNotExist:
        return JsonResponse({"error": "No children data found"}, status=404)

    except Exception:
        # Log the exception here if logging is set up
        return JsonResponse(
            {"error": "An error occurred while fetching the data"}, status=500
        )


# =================================== Children Birthday Graph ===================================
@login_required
@admin_or_manager_or_staff_required
def birthdays_by_month(request):
    # Query all children with non-null date_of_birth
    children = Child.objects.filter(date_of_birth__isnull=False)

    # Extract month
    months = [child.date_of_birth.month for child in children]

    # Count occurrences per month
    month_counts = [months.count(month) for month in range(1, 13)]

    # Prepare the response data
    response_data = {
        "months": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        "counts": month_counts,
    }

    return JsonResponse(response_data)


# =================================== Sponsor Payments - Children ===================================
def get_payments_children(request):
    payments_per_year = (
        ChildPayments.objects.annotate(year=ExtractYear("payment_date"))
        .values("year")
        .annotate(total_amount=Sum("amount"))
        .order_by("year")
    )
    data = list(payments_per_year)
    return JsonResponse(data, safe=False)


# =================================== Sponsor Payments - Staff ===================================
def get_payments_staff(request):
    payments_per_year = (
        StaffPayments.objects.annotate(year=ExtractYear("payment_date"))
        .values("year")
        .annotate(total_amount=Sum("amount"))
        .order_by("year")
    )
    data = list(payments_per_year)
    return JsonResponse(data, safe=False)


# =================================== INVENTORY DASHBOARD ===================================
@login_required
@admin_or_manager_or_staff_required
def get_total_sales_for_period(start_date, end_date):
    return (
        Sale.objects.filter(trans_date__range=[start_date, end_date]).aggregate(
            total_sales=Sum("grand_total")
        )["total_sales"]
        or 0
    )


@login_required
@admin_or_manager_or_staff_required
def inventory_dashboard(request):
    today = date.today()
    year = today.year

    # Helper function to get total sales for a period
    def get_total_sales_for_period(start_date, end_date):
        return (
            Sale.objects.filter(trans_date__range=[start_date, end_date]).aggregate(
                total_sales=Coalesce(Sum("grand_total"), 0.0)
            )["total_sales"]
            or 0
        )

    # Calculate monthly and annual earnings
    monthly_earnings = [
        Sale.objects.filter(trans_date__year=year, trans_date__month=month).aggregate(
            total=Coalesce(Sum("grand_total"), 0.0)
        )["total"]
        for month in range(1, 13)
    ]
    annual_earnings = format(sum(monthly_earnings), ".2f")
    avg_month = format(sum(monthly_earnings) / 12, ".2f")

    # Get total sales for today, week, and month
    total_sales_today = get_total_sales_for_period(today, today)
    total_sales_week = get_total_sales_for_period(
        today - timedelta(days=today.weekday()), today
    )
    total_sales_month = get_total_sales_for_period(today.replace(day=1), today)

    # Get top-selling products using the new method
    top_products = get_top_selling_products()

    # Total stock from Inventory
    total_stock = Product.objects.filter(status="ACTIVE").aggregate(
        total=Coalesce(Sum("inventory__quantity"), 0)
    )["total"]

    context = {
        "products": Product.objects.filter(status="ACTIVE").count(),
        "total_stock": total_stock,
        "categories": Category.objects.count(),
        "annual_earnings": annual_earnings,
        "monthly_earnings": json.dumps(monthly_earnings),
        "avg_month": avg_month,
        "total_sales_today": total_sales_today,
        "total_sales_week": total_sales_week,
        "total_sales_month": total_sales_month,
        "top_products": top_products,
    }

    return render(request, "main/inventory_dashboard.html", context)


@login_required
@admin_or_manager_or_staff_required
def monthly_earnings_view(request):
    today = date.today()
    year = today.year
    monthly_earnings = []

    for month in range(1, 13):
        earning = (
            Sale.objects.filter(trans_date__year=year, trans_date__month=month)
            .aggregate(
                total_variable=Coalesce(
                    Sum(F("grand_total")), 0.0, output_field=FloatField()
                )
            )
            .get("total_variable")
        )
        monthly_earnings.append(earning)

    return JsonResponse(
        {
            "labels": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
            "data": monthly_earnings,
        }
    )


# =================================== Annual Sales graph ===================================
@login_required
@admin_or_manager_or_staff_required
def sales_data_api(request):
    # Query to get total sales grouped by year
    sales_per_year = (
        Sale.objects.annotate(year=ExtractYear("trans_date"))
        .values("year")
        .annotate(total_sales=Sum("grand_total"))
        .order_by("year")
    )

    # Prepare the data as a dictionary
    data = {
        "years": [item["year"] for item in sales_per_year],
        "total_sales": [item["total_sales"] for item in sales_per_year],
    }

    # Return the data as JSON
    return JsonResponse(data)


# =================================== LOANS DASHBOARD ===================================
@login_required
@admin_or_manager_or_staff_required
def loans_dashboard(request):
    # Count loans by status
    new_loan_applications = Loan.objects.filter(status="pending").count()
    approved_loans = Loan.objects.filter(status="approved").count()
    closed_loans = Loan.objects.filter(status="closed").count()
    rejected_loans = Loan.objects.filter(status="rejected").count()
    loans_issued = Loan.objects.filter(status="disbursed").count()
    active_loans = Loan.objects.filter(status="disbursed").count()  # Adjust as needed
    overdue_loans = Loan.objects.filter(status="overdue").count()

    # Total repayments
    total_repayments = LoanRepayment.objects.aggregate(
        total_principal=Sum("principal_payment"),
        total_interest=Sum("interest_payment"),
    )

    # Calculate total repayments as a dictionary
    total_repayments_amount = {
        "total_principal": total_repayments["total_principal"] or 0,
        "total_interest": total_repayments["total_interest"] or 0,
        "total_amount": (total_repayments["total_principal"] or 0)
        + (total_repayments["total_interest"] or 0),
    }

    # Calculate total loan receivable and total interest receivable
    total_loans = Loan.objects.filter(status="disbursed").aggregate(
        total_loan_receivable=Sum(
            "principal_amount"
        ),  # Total principal amount of all loans
        total_interest_receivable=Sum(
            "total_interest"
        ),  # Total interest amount from loans
    )

    # Prepare the total loan amounts
    total_loans_amount = {
        "total_loan_receivable": (total_loans["total_loan_receivable"] or 0)
        - total_repayments_amount["total_principal"],
        "total_interest_receivable": (total_loans["total_interest_receivable"] or 0)
        - total_repayments_amount["total_interest"],
    }

    # Ensure values don't drop below zero
    total_loans_amount["total_loan_receivable"] = max(
        total_loans_amount["total_loan_receivable"], 0
    )
    total_loans_amount["total_interest_receivable"] = max(
        total_loans_amount["total_interest_receivable"], 0
    )

    context = {
        "new_loan_applications": new_loan_applications,
        "approved_loans": approved_loans,
        "closed_loans": closed_loans,
        "rejected_loans": rejected_loans,
        "loans_issued": loans_issued,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
        "total_repayments": total_repayments_amount,
        "total_loans": total_loans_amount,  # Add total loans to the context
    }

    return render(request, "main/loans_dashboard.html", context)
