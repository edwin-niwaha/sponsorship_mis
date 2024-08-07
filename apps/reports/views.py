from django.shortcuts import render
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib.auth.decorators import login_required

from apps.child.models import (
    Child,
    ChildCorrespondence,
    ChildDepart,
    ChildIncident,
    ChildProfilePicture,
    ChildProgress,
)

from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)


# =================================== Reports Dashboard ===================================
@login_required
@admin_or_manager_or_staff_required
def reports_dash(request):
    return render(request, "main/reports/_reports_dash_.html")


# =================================== All Children List ===================================
@login_required
@admin_or_manager_or_staff_required
def all_children_list(request):
    queryset = Child.objects.all().order_by("id")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(full_name__icontains=search_query)

    paginator = Paginator(queryset, 25)  # Show 25 records per page
    page = request.GET.get("page")

    try:
        records = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        records = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        records = paginator.page(paginator.num_pages)

    return render(
        request,
        "main/reports/all_children_list.html",
        {"records": records, "table_title": "All Children List"},
    )
