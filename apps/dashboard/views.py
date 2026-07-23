import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear, Greatest
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.child.models import Child
from apps.finance.models import ChildPayments, StaffPayments
from apps.inventory.products.models import Category, Product
from apps.inventory.sales.models import Sale
from apps.loans.models import Loan, LoanDisbursement, LoanRepayment
from apps.loans.services.reporting import loan_financial_row, portfolio_at_risk_summary
from apps.sponsor.models import Sponsor
from apps.sponsorship.models import ChildSponsorship, StaffSponsorship
from apps.users.decorators import admin_or_manager_or_staff_required

from django.core.cache import cache
from django.db.models import (
    Case, Count, DecimalField, F, FloatField, OuterRef, Q, Subquery, Sum, Value, When,
)

CACHE_KEY = "loans_dashboard_v3"
CACHE_TTL = 300  # 5 minutes

# Cap how many individual loan rows we pull into memory for the "list" view.
# Totals (total_due_today / total_overdue) are computed separately at the DB
# level, so this cap does NOT affect the accuracy of the summary numbers —
# it only limits how many rows we render/iterate in Python.
MAX_LOANS_PER_LIST = 50

ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=15, decimal_places=2))

logger = logging.getLogger(__name__)


from .utils import get_top_selling_products


def home(request):
    return render(request, "accounts/home.html")


CACHE_KEY = "loan_dashboard_summary"
CACHE_TTL = 300  # seconds (5 minutes)
DASHBOARD_OVERVIEW_CACHE_KEY = "sponsorship_dashboard_overview"


def get_loan_dashboard_summary(force_refresh=False):
    """
    Centralized, cached loan dashboard logic.
    Used by views and context processors.
    """

    if not force_refresh:
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached

    today = timezone.now().date()

    loans = Loan.objects.filter(status__in=["disbursed", "overdue"]).prefetch_related(
        "repayments", "penalties"
    )

    due_loans = []
    overdue_loans = []

    for loan in loans:
        balances = loan.calculate_remaining_balances()
        total_balance = (
            balances["principal_balance"]
            + balances["interest_balance"]
            + balances["penalty_balance"]
        )

        if total_balance <= 0:
            continue

        # ---------- OVERDUE (loan maturity passed) ----------
        if loan.due_date and loan.due_date < today:
            overdue_loans.append(
                {
                    "loan": loan,
                    "total_balance": total_balance,
                    "days_overdue": (today - loan.due_date).days,
                }
            )
            continue

        # ---------- DUE TODAY ----------
        schedule = loan.generate_payment_schedule()
        due_today = [
            p
            for p in schedule
            if p["payment_due_date"] == today
            and (p["principal_payment"] + p["interest_payment"]) > 0
        ]

        if due_today:
            amount_due = min(
                due_today[0]["principal_payment"] + due_today[0]["interest_payment"],
                total_balance,
            )
            due_loans.append(
                {
                    "loan": loan,
                    "amount_due": amount_due,
                    "total_balance": total_balance,
                }
            )

    summary = {
        "due_loans": due_loans,
        "overdue_loans": overdue_loans,
        "due_loans_count": len(due_loans),
        "overdue_loans_count": len(overdue_loans),
        "due_loans_total": sum(
            (loan_info["amount_due"] for loan_info in due_loans),
            Decimal("0.00"),
        ),
        "overdue_loans_total": sum(
            (loan_info["total_balance"] for loan_info in overdue_loans),
            Decimal("0.00"),
        ),
    }

    cache.set(CACHE_KEY, summary, CACHE_TTL)
    return summary


# =================================== The dashboard ===================================


@login_required
@admin_or_manager_or_staff_required
def dashboard(request):
    context = cache.get(DASHBOARD_OVERVIEW_CACHE_KEY)
    if context is None:
        top_sponsors = get_top_sponsors()
        top_children = get_top_children_sponsored()
        top_staff = get_top_staff_sponsored()
        context = {
            "sponsors_count": Sponsor.objects.active_real_supporters().count(),
            "children_count": Child.objects.count(),
            "children_departed_count": Child.objects.filter(is_departed=True).count(),
            "sponsored_count": Child.objects.filter(
                is_departed=False,
                is_sponsored=True,
            ).count(),
            "non_sponsored_count": Child.objects.filter(
                is_departed=False,
                is_sponsored=False,
            ).count(),
            "top_sponsors_with_counts": list(
                zip(top_sponsors["sponsors"], top_sponsors["counts"])
            ),
            "top_children_with_counts": list(
                zip(top_children["children"], top_children["counts"])
            ),
            "top_staff_with_counts": list(
                zip(top_staff["staff_active"], top_staff["counts"])
            ),
        }
        cache.set(DASHBOARD_OVERVIEW_CACHE_KEY, context, 300)

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
    categories = (
        ("Child Sponsors", Sponsor.objects.child_sponsors()),
        ("Staff Sponsors", Sponsor.objects.staff_sponsors()),
        ("Family Supporters", Sponsor.objects.family_supporters()),
        ("General Donors", Sponsor.objects.general_donors()),
        ("One-time Donors", Sponsor.objects.one_time_donors()),
    )
    data = [
        {"sponsorship_type": label, "count": queryset.active().count()}
        for label, queryset in categories
    ]
    return JsonResponse(data, safe=False)


# =================================== Sponsors Graph ===================================
@login_required
@admin_or_manager_or_staff_required
def get_sponsors_data(request):
    try:
        sponsors_per_year = (
            Sponsor.objects.real_sponsors_only()
            .annotate(year=ExtractYear("start_date"))
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
            Sponsor.objects.real_sponsors_only()
            .annotate(year=ExtractYear("start_date"))
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

    # Calculate total profit from all sales
    total_profit = sum(
        sum(detail.calculate_profit() for detail in sale.items.all())
        for sale in Sale.objects.all()
    )

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
        "total_profit": format(total_profit, ".2f"),
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


# @login_required
# @admin_or_manager_or_staff_required
# def loans_dashboard(request):
#     today = timezone.now().date()
#     year = today.year

#     # Loan counts
#     new_loan_applications = Loan.objects.filter(status="pending").count()
#     approved_loans = Loan.objects.filter(
#         status__in=["approved", "boo_approved", "hof_approved", "ed_approved"]
#     ).count()
#     rejected_loans = Loan.objects.filter(
#         status__in=["rejected", "ed_rejected", "hof_rejected"]
#     ).count()
#     disbursed_loans = (
#         Loan.objects.filter(status__in=["disbursed", "overdue", "repaid"])
#         .prefetch_related("disbursements")
#         .count()
#     )
#     closed_loans = Loan.objects.filter(status="closed").count()
#     repaid_loans = Loan.objects.filter(status="repaid").count()

#     # Initialize aggregates
#     due_loans = []
#     overdue_loans = []
#     total_principal_receivable = Decimal("0.00")
#     total_interest_receivable = Decimal("0.00")
#     total_penalty_receivable = Decimal("0.00")

#     # Process loans for due/overdue and receivables
#     loans = Loan.objects.filter(status__in=["disbursed", "overdue"]).select_related(
#         "borrower"
#     )
#     for loan in loans:
#         try:
#             if not loan.disbursement_date or loan.loan_period_months <= 0:
#                 continue
#             balances = loan.calculate_remaining_balances()
#             total_balance = (
#                 balances["principal_balance"]
#                 + balances["interest_balance"]
#                 + balances["penalty_balance"]
#             )
#             if total_balance <= 0:
#                 continue

#             # Update receivables
#             total_principal_receivable += balances["principal_balance"]
#             total_interest_receivable += balances["interest_balance"]
#             total_penalty_receivable += balances["penalty_balance"]

#             # Due and overdue calculations
#             schedule = loan.generate_payment_schedule()
#             total_amount_due = total_balance  # Default to total balance
#             due_payments = [
#                 p
#                 for p in schedule
#                 if isinstance(p["payment_due_date"], (date, datetime))
#                 and (
#                     p["payment_due_date"].date()
#                     if isinstance(p["payment_due_date"], datetime)
#                     else p["payment_due_date"]
#                 )
#                 == today
#                 and p["principal_payment"] + p["interest_payment"] > 0
#             ]
#             if due_payments:
#                 total_amount_due = min(
#                     sum(
#                         p["principal_payment"] + p["interest_payment"]
#                         for p in due_payments
#                     ),
#                     total_balance,
#                 )
#                 total_amount_due_balance = loan.calculate_total_amount_due_balance(
#                     due_date=today, total_amount_due=total_amount_due
#                 )
#                 if total_amount_due_balance > 0:
#                     due_loans.append(
#                         {
#                             "total_balance": total_balance,
#                             "total_amount_due_balance": total_amount_due_balance,
#                             "penalty_balance": balances["penalty_balance"],
#                         }
#                     )

#             overdue_payments = [
#                 p
#                 for p in schedule
#                 if isinstance(p["payment_due_date"], (date, datetime))
#                 and (
#                     p["payment_due_date"].date()
#                     if isinstance(p["payment_due_date"], datetime)
#                     else p["payment_due_date"]
#                 )
#                 < today
#                 and p["principal_payment"] + p["interest_payment"] > 0
#             ]
#             if overdue_payments or (loan.due_date and loan.due_date < today):
#                 total_amount_due = (
#                     total_balance
#                     if (loan.due_date and loan.due_date < today)
#                     else min(
#                         sum(
#                             p["principal_payment"] + p["interest_payment"]
#                             for p in overdue_payments
#                         ),
#                         total_balance,
#                     )
#                 )
#                 total_amount_due_balance = loan.calculate_total_amount_due_balance(
#                     due_date=today, total_amount_due=total_amount_due
#                 )
#                 if total_amount_due_balance > 0:
#                     overdue_loans.append(
#                         {
#                             "total_balance": total_balance,
#                             "total_amount_due_balance": total_amount_due_balance,
#                             "penalty_balance": balances["penalty_balance"],
#                         }
#                     )
#         except Exception as e:
#             logger.error(f"Error processing loan {loan.id}: {e}")
#             continue

#     # Aggregates for due/overdue
#     due_loans_count = len(due_loans)
#     due_loans_total_due_balance = sum(
#         loan["total_amount_due_balance"] for loan in due_loans
#     )
#     due_loans_total_penalty_balance = sum(loan["penalty_balance"] for loan in due_loans)
#     due_loans_total_balance = sum(loan["total_balance"] for loan in due_loans)
#     overdue_loans_count = len(overdue_loans)
#     overdue_loans_total_due_balance = sum(
#         loan["total_amount_due_balance"] for loan in overdue_loans
#     )
#     overdue_loans_total_penalty_balance = sum(
#         loan["penalty_balance"] for loan in overdue_loans
#     )
#     overdue_loans_total_balance = sum(loan["total_balance"] for loan in overdue_loans)

#     # Repayments
#     total_repayments = LoanRepayment.objects.aggregate(
#         total_principal=Sum("principal_payment", default=Decimal("0.00")),
#         total_interest=Sum("interest_payment", default=Decimal("0.00")),
#         total_penalty=Sum("penalty_payment", default=Decimal("0.00")),
#     )
#     total_repayments_amount = {
#         "total_principal": total_repayments["total_principal"] or Decimal("0.00"),
#         "total_interest": total_repayments["total_interest"] or Decimal("0.00"),
#         "total_penalty": total_repayments["total_penalty"] or Decimal("0.00"),
#         "total_amount": (
#             (total_repayments["total_principal"] or Decimal("0.00"))
#             + (total_repayments["total_interest"] or Decimal("0.00"))
#             + (total_repayments["total_penalty"] or Decimal("0.00"))
#         ),
#     }

#     # Receivables
#     total_loans_amount = {
#         "total_principal_receivable": max(total_principal_receivable, Decimal("0.00")),
#         "total_interest_receivable": max(total_interest_receivable, Decimal("0.00")),
#         "total_penalty_receivable": max(total_penalty_receivable, Decimal("0.00")),
#         "total_outstanding": max(
#             total_principal_receivable
#             + total_interest_receivable
#             + total_penalty_receivable,
#             Decimal("0.00"),
#         ),
#     }

#     portfolio_rows = [
#         loan_financial_row(loan, today=today)
#         for loan in (
#             Loan.objects.filter(status__in=["disbursed", "overdue"])
#             .select_related("borrower", "account", "applied_by")
#             .prefetch_related("repayments", "penalties")
#         )
#     ]
#     par_summary = portfolio_at_risk_summary(portfolio_rows)
#     par_30_band = next(
#         (band for band in par_summary["bands"] if band["bucket"] == "PAR 30+"),
#         None,
#     )
#     portfolio_at_risk_rate = (
#         par_30_band["portfolio_percent"] if par_30_band else Decimal("0.00")
#     )
#     portfolio_at_risk_amount = (
#         par_30_band["outstanding_amount"] if par_30_band else Decimal("0.00")
#     )

#     months = [
#         "Jan",
#         "Feb",
#         "Mar",
#         "Apr",
#         "May",
#         "Jun",
#         "Jul",
#         "Aug",
#         "Sep",
#         "Oct",
#         "Nov",
#         "Dec",
#     ]
#     monthly_disbursements = [0 for _ in range(12)]
#     for item in (
#         LoanDisbursement.objects.filter(loan__disbursement_date__year=year)
#         .annotate(month=ExtractMonth("loan__disbursement_date"))
#         .values("month")
#         .annotate(total=Coalesce(Sum("loan__principal_amount"), Decimal("0.00")))
#     ):
#         if item["month"]:
#             monthly_disbursements[item["month"] - 1] = float(item["total"] or 0)

#     monthly_repayments = [0 for _ in range(12)]
#     for item in (
#         LoanRepayment.objects.filter(repayment_date__year=year)
#         .annotate(month=ExtractMonth("repayment_date"))
#         .values("month")
#         .annotate(
#             total=Coalesce(
#                 Sum("principal_payment")
#                 + Sum("interest_payment")
#                 + Sum("penalty_payment"),
#                 Decimal("0.00"),
#             )
#         )
#     ):
#         if item["month"]:
#             monthly_repayments[item["month"] - 1] = float(item["total"] or 0)

#     purpose_labels = dict(Loan.LOAN_PURPOSE_CHOICES)
#     purpose_mix = (
#         Loan.objects.values("loan_purpose")
#         .annotate(count=Count("id"))
#         .order_by("-count")
#     )
#     loan_purpose_chart = {
#         "labels": [
#             purpose_labels.get(item["loan_purpose"], item["loan_purpose"] or "Unknown")
#             for item in purpose_mix
#         ],
#         "data": [item["count"] for item in purpose_mix],
#     }

#     loan_dashboard_charts = {
#         "pipeline": {
#             "labels": ["New", "Approved", "Disbursed", "Repaid", "Closed", "Rejected"],
#             "data": [
#                 new_loan_applications,
#                 approved_loans,
#                 disbursed_loans,
#                 repaid_loans,
#                 closed_loans,
#                 rejected_loans,
#             ],
#         },
#         "risk": {
#             "labels": ["Due today", "Overdue"],
#             "data": [due_loans_count, overdue_loans_count],
#         },
#         "repayments": {
#             "labels": ["Principal", "Interest", "Penalties"],
#             "data": [
#                 float(total_repayments_amount["total_principal"]),
#                 float(total_repayments_amount["total_interest"]),
#                 float(total_repayments_amount["total_penalty"]),
#             ],
#         },
#         "receivables": {
#             "labels": ["Principal", "Interest", "Penalties"],
#             "data": [
#                 float(total_loans_amount["total_principal_receivable"]),
#                 float(total_loans_amount["total_interest_receivable"]),
#                 float(total_loans_amount["total_penalty_receivable"]),
#             ],
#         },
#         "cashflow": {
#             "labels": months,
#             "disbursements": monthly_disbursements,
#             "repayments": monthly_repayments,
#         },
#         "purpose": loan_purpose_chart,
#     }

#     # Recent activity
#     recent_activity = []
#     for repayment in LoanRepayment.objects.select_related("loan").order_by(
#         "-repayment_date"
#     )[:5]:
#         try:
#             balances = repayment.loan.calculate_remaining_balances()
#             total_balance = (
#                 balances["principal_balance"]
#                 + balances["interest_balance"]
#                 + balances["penalty_balance"]
#             )
#             recent_activity.append(
#                 {
#                     "type": "Repayment",
#                     "loan_id": repayment.loan.id,
#                     "amount": repayment.total_payment,
#                     "date": repayment.repayment_date,
#                     "total_balance": total_balance,
#                     "status": repayment.loan.status,
#                 }
#             )
#         except Exception as e:
#             logger.error(
#                 f"Error processing repayment for loan {repayment.loan.id}: {e}"
#             )
#             continue

#     for disbursement in LoanDisbursement.objects.select_related("loan").order_by(
#         "-loan__disbursement_date"
#     )[:5]:
#         try:
#             if not disbursement.loan.disbursement_date:
#                 continue
#             balances = disbursement.loan.calculate_remaining_balances()
#             total_balance = (
#                 balances["principal_balance"]
#                 + balances["interest_balance"]
#                 + balances["penalty_balance"]
#             )
#             recent_activity.append(
#                 {
#                     "type": "Disbursement",
#                     "loan_id": disbursement.loan.id,
#                     "amount": disbursement.disbursed_amount,
#                     "date": disbursement.loan.disbursement_date,
#                     "total_balance": total_balance,
#                     "status": disbursement.loan.status,
#                 }
#             )
#         except Exception as e:
#             logger.error(
#                 f"Error processing disbursement for loan {disbursement.loan.id}: {e}"
#             )
#             continue
#     recent_activity = sorted(recent_activity, key=lambda x: x["date"], reverse=True)[:5]

#     context = {
#         "new_loan_applications": new_loan_applications,
#         "approved_loans": approved_loans,
#         "rejected_loans": rejected_loans,
#         "disbursed_loans": disbursed_loans,
#         "closed_loans": closed_loans,
#         "repaid_loans": repaid_loans,
#         "portfolio_at_risk_rate": portfolio_at_risk_rate,
#         "portfolio_at_risk_amount": portfolio_at_risk_amount,
#         "due_loans_count": due_loans_count,
#         "due_loans_total_due_balance": due_loans_total_due_balance,
#         "due_loans_total_penalty_balance": due_loans_total_penalty_balance,
#         "due_loans_total_balance": due_loans_total_balance,
#         "overdue_loans_count": overdue_loans_count,
#         "overdue_loans_total_due_balance": overdue_loans_total_due_balance,
#         "overdue_loans_total_penalty_balance": overdue_loans_total_penalty_balance,
#         "overdue_loans_total_balance": overdue_loans_total_balance,
#         "total_repayments": total_repayments_amount,
#         "total_loans": total_loans_amount,
#         "recent_activity": recent_activity,
#         "loan_dashboard_charts": loan_dashboard_charts,
#     }

#     return render(request, "main/loans_dashboard.html", context)


def loans_dashboard(request):
    context = cache.get(CACHE_KEY)
    if context is not None:
        return render(request, "main/loans_dashboard.html", context)
 
    context = _build_dashboard_context()
    cache.set(CACHE_KEY, context, timeout=CACHE_TTL)
 
    return render(request, "main/loans_dashboard.html", context)
 
 
def _annotate_remaining_balance(queryset):
    """
    Mirrors Loan.calculate_remaining_balances() exactly, but computed for an
    entire queryset in a single query instead of once per loan in Python:
 
        principal_balance = max(principal_amount - paid_principal, 0)
        interest_balance  = max(total_interest  - paid_interest,  0)
        penalty_balance   = sum of unpaid, non-deleted LoanPenalty.remaining_amount
        remaining_balance = principal_balance + interest_balance + penalty_balance
 
    Each correlated Subquery below runs as part of the single query's
    execution plan (no per-row Python queries), which is what avoids the
    N+1 that calling loan.calculate_remaining_balances() per loan causes.
    """
    from apps.loans.models import LoanRepayment, LoanPenalty  # adjust import path
 
    paid_principal_sq = (
        LoanRepayment.objects.filter(loan_id=OuterRef("pk"))
        .values("loan_id")
        .annotate(total=Sum("principal_payment"))
        .values("total")
    )
    paid_interest_sq = (
        LoanRepayment.objects.filter(loan_id=OuterRef("pk"))
        .values("loan_id")
        .annotate(total=Sum("interest_payment"))
        .values("total")
    )
    unpaid_penalty_sq = (
        LoanPenalty.objects.filter(loan_id=OuterRef("pk"), is_paid=False, is_deleted=False)
        .values("loan_id")
        .annotate(total=Sum("remaining_amount"))
        .values("total")
    )
 
    return queryset.annotate(
        paid_principal=Coalesce(Subquery(paid_principal_sq, output_field=DecimalField()), ZERO),
        paid_interest=Coalesce(Subquery(paid_interest_sq, output_field=DecimalField()), ZERO),
        principal_balance=Greatest(
            F("principal_amount") - F("paid_principal"), ZERO
        ),
        interest_balance=Greatest(
            Coalesce(F("total_interest"), ZERO) - F("paid_interest"), ZERO
        ),
        penalty_balance=Coalesce(Subquery(unpaid_penalty_sq, output_field=DecimalField()), ZERO),
    ).annotate(
        remaining_balance=F("principal_balance") + F("interest_balance") + F("penalty_balance")
    )
 
 
def _build_dashboard_context():
    from apps.loans.models import Loan, LoanRepayment  # adjust import path
 
    today = timezone.now().date()
    current_year = today.year
 
    active_loans = Loan.objects.filter(status__in=Loan.ACTIVE_STATUSES).select_related(
        "borrower"
    )
 
    # ------------------------------------------------------------------
    # 1. Portfolio summary
    # ------------------------------------------------------------------
    portfolio_summary = active_loans.aggregate(
        total_loans=Count("id"),
        total_principal=Sum("principal_amount"),
    )
    total_loans = portfolio_summary["total_loans"] or 0
    total_principal = portfolio_summary["total_principal"] or Decimal("0")
 
    # ------------------------------------------------------------------
    # 2. Repayments summary — total_payment is a Python @property
    #    (principal_payment + interest_payment + penalty_payment), not a
    #    DB column, so it has to be summed as three separate DB fields
    #    instead of Sum("total_payment").
    # ------------------------------------------------------------------
    repayments_summary = LoanRepayment.objects.aggregate(
        total_principal=Coalesce(Sum("principal_payment"), ZERO),
        total_interest=Coalesce(Sum("interest_payment"), ZERO),
        total_penalty=Coalesce(Sum("penalty_payment"), ZERO),
    )
    total_repaid = (
        repayments_summary["total_principal"]
        + repayments_summary["total_interest"]
        + repayments_summary["total_penalty"]
    )
 
    # ------------------------------------------------------------------
    # 3. Monthly disbursements
    # ------------------------------------------------------------------
    disbursements = (
        Loan.objects.filter(disbursement_date__year=current_year)
        .values("disbursement_date__month")
        .annotate(total=Sum("principal_amount"))
        .order_by("disbursement_date__month")
    )
    monthly_disbursements = {m: 0 for m in range(1, 13)}
    for d in disbursements:
        monthly_disbursements[d["disbursement_date__month"]] = float(d["total"] or 0)
 
    # ------------------------------------------------------------------
    # 4. Due & overdue — one query, DB-computed balances, DB-computed totals
    # ------------------------------------------------------------------
    balanced_loans = _annotate_remaining_balance(active_loans)
    due_or_overdue = balanced_loans.filter(Q(due_date=today) | Q(due_date__lt=today))
 
    totals = due_or_overdue.aggregate(
        total_due_today=Coalesce(
            Sum(Case(When(due_date=today, then=F("remaining_balance")), default=ZERO)),
            ZERO,
        ),
        total_overdue=Coalesce(
            Sum(Case(When(due_date__lt=today, then=F("remaining_balance")), default=ZERO)),
            ZERO,
        ),
    )
    total_due_today = totals["total_due_today"]
    total_overdue = totals["total_overdue"]
 
    display_rows = list(
        due_or_overdue.only(
            "id", "principal_amount", "total_interest", "due_date", "status", "borrower_id"
        ).order_by("due_date")[:MAX_LOANS_PER_LIST]
    )
 
    due_loans = [
        {"loan": loan, "total_balance": loan.remaining_balance}
        for loan in display_rows
        if loan.due_date == today
    ]
    overdue_loans = [
        {"loan": loan, "total_balance": loan.remaining_balance}
        for loan in display_rows
        if loan.due_date < today
    ]
 
    # ------------------------------------------------------------------
    # 5. PAR (Portfolio at Risk)
    # ------------------------------------------------------------------
    par = (total_overdue / (total_principal or Decimal("1"))) * 100
 
    # ------------------------------------------------------------------
    # 6. Recent activity — evaluated to plain lists before caching
    # ------------------------------------------------------------------
    recent_repayments = list(
        LoanRepayment.objects.select_related("loan")
        .only("loan_id", "principal_payment", "interest_payment", "penalty_payment", "repayment_date")
        .order_by("-repayment_date")[:5]
    )
    recent_disbursements = list(
        Loan.objects.select_related("borrower")
        .only("borrower_id", "principal_amount", "disbursement_date")
        .order_by("-disbursement_date")[:5]
    )
 
    return {
        "total_loans": total_loans,
        "total_principal": total_principal,
        "total_repaid": total_repaid,
        "monthly_disbursements": list(monthly_disbursements.values()),
        "due_loans": due_loans,
        "overdue_loans": overdue_loans,
        "due_loans_truncated": len(display_rows) >= MAX_LOANS_PER_LIST,
        "total_due_today": total_due_today,
        "total_overdue": total_overdue,
        "par": round(par, 2),
        "recent_repayments": recent_repayments,
        "recent_disbursements": recent_disbursements,
    }