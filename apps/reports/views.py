from collections import defaultdict
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

from apps.child.models import Child
from apps.sponsorship.models import ChildSponsorship, StaffSponsorship
from apps.sponsor.models import Sponsor
from apps.staff.models import Staff
from apps.finance.models import ChildPayments, StaffPayments
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

# =================================== Helper Functions ===================================


def paginate_queryset(queryset, page_number, per_page=50):
    """
    Paginate the given queryset and return the records for the specified page number.
    """
    paginator = Paginator(queryset, per_page)
    try:
        records = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        records = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page of results.
        records = paginator.page(paginator.num_pages)
    return records


def filter_by_search(queryset, search_query, search_fields):
    """
    Filter the queryset by the search query over the given fields.
    """
    if search_query:
        filters = {f"{field}__icontains": search_query for field in search_fields}
        queryset = queryset.filter(**filters)
    return queryset


# =================================== Reports Dashboard ===================================


@login_required
@admin_or_manager_or_staff_required
def reports_dash(request):
    """
    Render the reports dashboard with counts of sponsors, children, and staff.
    """
    # Sponsors
    sponsors_count = Sponsor.objects.filter(is_departed=False).count()
    sponsors_departed_count = Sponsor.objects.filter(is_departed=True).count()

    # Children
    children_count = Child.objects.count()
    sponsored_count = ChildSponsorship.objects.filter(is_active=True).count()
    non_sponsored_count = Child.objects.filter(
        is_departed=False, is_sponsored=False
    ).count()
    children_departed_count = Child.objects.filter(is_departed=True).count()

    # Staff
    staff_count = Staff.objects.count()
    sponsored_staff_count = StaffSponsorship.objects.filter(is_active=True).count()
    non_sponsored_staff_count = Staff.objects.filter(
        is_departed=False, is_sponsored=False
    ).count()
    departed_staff_count = Staff.objects.filter(is_departed=True).count()

    context = {
        # Sponsors
        "sponsors_count": sponsors_count,
        "sponsors_departed_count": sponsors_departed_count,
        # Children
        "children_count": children_count,
        "children_departed_count": children_departed_count,
        "sponsored_count": sponsored_count,
        "non_sponsored_count": non_sponsored_count,
        # Staff
        "staff_count": staff_count,
        "sponsored_staff_count": sponsored_staff_count,
        "non_sponsored_staff_count": non_sponsored_staff_count,
        "departed_staff_count": departed_staff_count,
    }
    return render(request, "sdms/reports/_reports_dash_.html", context)


# =================================== All Children Master List ===================================


@login_required
@admin_or_manager_or_staff_required
def children_master_list(request):
    queryset = (
        ChildSponsorship.objects.filter(is_active=True)
        .select_related("child", "sponsor")
        .order_by("child", "id")
    )
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["child__full_name"])

    # Group the queryset by child
    grouped_sponsorships = defaultdict(list)
    for sponsorship in queryset:
        grouped_sponsorships[sponsorship.child].append(sponsorship)

    page = request.GET.get("page")
    records = paginate_queryset(list(grouped_sponsorships.items()), page)

    return render(
        request,
        "sdms/reports/children_master_list.html",
        {"records": records, "table_title": "Children Master List"},
    )


# =================================== All Children List ===================================


@login_required
@admin_or_manager_or_staff_required
def all_children(request):
    """
    Render a paginated list of all children.
    """
    queryset = Child.objects.all().order_by("id")
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["full_name"])

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/all_children.html",
        {"records": records, "table_title": "All Children"},
    )


# =================================== All Sponsored Children List ===================================


@login_required
@admin_or_manager_or_staff_required
def sponsored_children(request):
    """
    Render a paginated list of all sponsored children, grouped by child.
    """
    queryset = (
        ChildSponsorship.objects.filter(is_active=True)
        .select_related("child", "sponsor")
        .order_by("child", "id")
    )
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["child__full_name"])

    # Group the queryset by child
    grouped_sponsorships = defaultdict(list)
    for sponsorship in queryset:
        grouped_sponsorships[sponsorship.child].append(sponsorship)

    page = request.GET.get("page")
    records = paginate_queryset(list(grouped_sponsorships.items()), page)

    return render(
        request,
        "sdms/reports/sponsored_children.html",
        {"records": records, "table_title": "All Sponsored Children"},
    )


# =================================== All Non Sponsored Children List ===================================


@login_required
@admin_or_manager_or_staff_required
def un_sponsored_children(request):
    """
    Render a paginated list of all non-sponsored children.
    """
    queryset = Child.objects.filter(is_departed=False, is_sponsored=False).order_by(
        "id"
    )
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["full_name"])

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/non_sponsored_children.html",
        {"records": records, "table_title": "All Non-Sponsored Children"},
    )


# =================================== All Departed Children List ===================================


@login_required
@admin_or_manager_or_staff_required
def departed_children(request):
    """
    Render a paginated list of all departed children.
    """
    queryset = (
        Child.objects.filter(is_departed=True)
        .order_by("id")
        .prefetch_related("departures")
    )
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["full_name"])

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/departed_children.html",
        {"records": records, "table_title": "All Departed Children"},
    )


# =================================== All Departed Sponsors List ===================================


@login_required
@admin_or_manager_or_staff_required
def departed_sponsors(request):
    """
    Render a paginated list of all departed sponsors.
    """
    queryset = Sponsor.objects.filter(is_departed=True).order_by("id")
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["first_name", "last_name"])

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/departed_sponsors.html",
        {"records": records, "table_title": "All Departed Sponsors"},
    )


# =================================== Child - Sponsor Payments ===================================
@login_required
@admin_or_manager_or_staff_required
def sponsor_payments_child(request):
    """
    Render a paginated list of all sponsor payments for children.
    """
    queryset = ChildPayments.objects.filter(is_valid=True).order_by("id")
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["first_name", "last_name"])

    # Calculate the total amount
    total_amount = queryset.aggregate(total_amount=Sum("amount"))["total_amount"] or 0

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/payments_child.html",
        {
            "records": records,
            "table_title": "Sponsor Payments - Child",
            "total_amount": total_amount,
        },
    )


# =================================== Staff - Sponsor Payments ===================================


@login_required
@admin_or_manager_or_staff_required
def sponsor_payments_staff(request):
    """
    Render a paginated list of all sponsor payments for staff.
    """
    queryset = StaffPayments.objects.filter(is_valid=True).order_by("id")
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["first_name", "last_name"])

    # Calculate the total amount
    total_amount = queryset.aggregate(total_amount=Sum("amount"))["total_amount"] or 0

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/payments_staff.html",
        {
            "records": records,
            "table_title": "Sponsor Payments - Staff",
            "total_amount": total_amount,
        },
    )


# =================================== All Sponsored Staff List ===================================


@login_required
@admin_or_manager_or_staff_required
def sponsored_staff(request):
    """
    Render a paginated list of all sponsored staff, grouped by staff.
    """
    queryset = (
        StaffSponsorship.objects.filter(is_active=True)
        .select_related("staff", "sponsor")
        .order_by("staff", "id")
    )
    search_query = request.GET.get("search")
    queryset = filter_by_search(
        queryset, search_query, ["staff__first_name", "staff__last_name"]
    )

    # Group the queryset by staff
    grouped_sponsorships = defaultdict(list)
    for sponsorship in queryset:
        grouped_sponsorships[sponsorship.staff].append(sponsorship)

    page = request.GET.get("page")
    records = paginate_queryset(list(grouped_sponsorships.items()), page)

    return render(
        request,
        "sdms/reports/sponsored_staff.html",
        {"records": records, "table_title": "All Sponsored Staff"},
    )


# =================================== All Non Sponsored Staff List ===================================


@login_required
@admin_or_manager_or_staff_required
def non_sponsored_staff(request):
    """
    Render a paginated list of all non-sponsored staff.
    """
    queryset = Staff.objects.filter(is_sponsored=False, is_departed=False).order_by(
        "id"
    )
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["first_name", "last_name"])

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/non_sponsored_staff.html",
        {"records": records, "table_title": "All Non-Sponsored Staff"},
    )


# =================================== All Departed Staff List ===================================


@login_required
@admin_or_manager_or_staff_required
def departed_staff(request):
    """
    Render a paginated list of all departed staff.
    """
    queryset = Staff.objects.filter(is_departed=True).order_by("id")
    search_query = request.GET.get("search")
    queryset = filter_by_search(queryset, search_query, ["first_name", "last_name"])

    page = request.GET.get("page")
    records = paginate_queryset(queryset, page)

    return render(
        request,
        "sdms/reports/departed_staff.html",
        {"records": records, "table_title": "All Departed Staff"},
    )
