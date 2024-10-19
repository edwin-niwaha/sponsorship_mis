from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from apps.sponsorship.models import ChildSponsorship, StaffSponsorship
from apps.users.decorators import admin_or_manager_or_staff_required
from apps.child.models import Child
from apps.sponsor.models import Sponsor
from apps.finance.models import ChildPayments, StaffPayments
from apps.users.models import Profile

from django.http import JsonResponse
from django.db.models.functions import ExtractYear


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

    except Exception as e:
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

    except Exception as e:
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

    except Exception as e:
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
