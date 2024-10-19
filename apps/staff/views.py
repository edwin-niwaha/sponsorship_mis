from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

from .forms import StaffDepartureForm, StaffForm
from .models import Staff, StaffDeparture


@login_required
@admin_or_manager_or_staff_required
def staff_list(request):
    queryset = Staff.objects.all().filter(is_departed=False).order_by("id")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(first_name__icontains=search_query).filter(
            last_name__icontains=search_query
        )

    paginator = Paginator(queryset, 50)
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
        "sdms/staff/staff_details.html",
        {"records": records, "table_title": "Staff List"},
    )


# =================================== Register Staff ===================================


@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def register_staff(request):
    if request.method == "POST":
        form = StaffForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.info(
                request, "Record saved successfully!", extra_tags="bg-success"
            )
            return redirect("register_staff")
        else:
            # Display an error message if the form is not valid
            messages.error(
                request,
                "There was an error saving the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )
    else:
        form = StaffForm()
    return render(
        request,
        "sdms/staff/staff_register.html",
        {"form_name": "Staff Registration", "form": form},
    )


# =================================== Update Staff data ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def update_staff(request, pk, template_name="sdms/staff/staff_register.html"):
    try:
        staff_record = Staff.objects.get(pk=pk)
    except Staff.DoesNotExist:
        messages.error(request, "Record not found!", extra_tags="bg-danger")
        return redirect("staff_list")  # Or a relevant error page

    if request.method == "POST":
        form = StaffForm(request.POST, request.FILES, instance=staff_record)
        if form.is_valid():
            form.save()

            messages.success(
                request, "Record updated successfully!", extra_tags="bg-success"
            )
            return redirect("staff_list")
            # Display an error message if the form is not valid
        else:
            messages.error(
                request,
                "There was an error saving the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )
    else:
        # Pre-populate the form with existing data
        form = StaffForm(instance=staff_record)

    context = {"form_name": "Staff Registration", "form": form}
    return render(request, template_name, context)


# =================================== Deleted selected Staff ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_staff(request, pk):
    records = Staff.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("staff_list"))


# =================================== Depart staff ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def staff_departure(request):
    if request.method == "POST":
        form = StaffDepartureForm(request.POST, request.FILES)
        if form.is_valid():
            staff_id = request.POST.get("id")
            staff_instance = get_object_or_404(Staff, pk=staff_id)

            # Create a StaffDeparture instance
            staff_depart = StaffDeparture.objects.create(staff=staff_instance)
            staff_depart.departure_date = form.cleaned_data["departure_date"]
            staff_depart.departure_reason = form.cleaned_data["departure_reason"]
            staff_depart.save()

            # Update Staff status to "departed"
            staff_instance.is_departed = True
            staff_instance.save()

            messages.success(
                request, "Staff departed successfully!", extra_tags="bg-success"
            )
            return redirect("staff_departure")
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = StaffDepartureForm()

    records = Staff.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/staff/staff_depature.html",
        {"form": form, "form_name": "Staff Depature Form", "records": records},
    )


# =================================== staff Depature Report ===================================
@login_required
@admin_or_manager_required
def staff_depature_list(request):
    queryset = (
        Staff.objects.all()
        .filter(is_departed=True)
        .order_by("id")
        .prefetch_related("departures")
    )

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(first_name__icontains=search_query).filter(
            last_name__icontains=search_query
        )

    paginator = Paginator(queryset, 50)
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
        "sdms/staff/staff_depature_list.html",
        {"records": records, "table_title": "Departed Staff"},
    )


# =================================== Reinstate departed staff ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def reinstate_staff(request, pk):
    staff = get_object_or_404(Staff, id=pk)

    if request.method == "POST":
        staff.is_departed = False
        staff.save()
        messages.success(
            request, "staff reinstated successfully!", extra_tags="bg-success"
        )

        return redirect("staff_depature_list")

    return render(request, "sdms/staff/staff_depature_list.html", {"staff": staff})
