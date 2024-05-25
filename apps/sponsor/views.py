from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    SponsorDepartForm,
    SponsorForm,
)
from .models import (
    Sponsor,
    SponsorDeparture,
)


@login_required
def sponsor_list(request):
    queryset = Sponsor.objects.all().filter(is_departed="No").order_by("id")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(first_name__icontains=search_query).filter(last_name__icontains=search_query)

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
        "main/sponsor/sponsor_details.html",
        {"records": records, "table_title": "Sponsors MasterList"},
    )

# =================================== Register Sponsor ===================================

@login_required
@transaction.atomic
def register_sponsor(request):
    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.info(
                request, "Record saved successfully!", extra_tags="bg-success"
            )

        else:
            # Display form errors
            return render(request, "main/sponsor/sponsor_register.html", {"form": form})
    else:
        form = SponsorForm()
    return render(
        request,
        "main/sponsor/sponsor_register.html",
        {"form_name": "Sponsor Registration", "form": form},
    )

# =================================== Update Sponsor data ===================================
@login_required
@transaction.atomic
def update_sponsor(request, pk, template_name="main/sponsor/sponsor_register.html"):
    try:
        sponsor_record = Sponsor.objects.get(pk=pk)
    except Sponsor.DoesNotExist:
        messages.error(request, "Record not found!")
        return redirect("sponsor_list")  # Or a relevant error page

    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES, instance=sponsor_record)
        if form.is_valid():
            form.save()

            messages.success(request, "Record updated successfully!")
            return redirect("sponsor_list")  # Replace with the appropriate redirect URL
    else:
        # Pre-populate the form with existing data
        form = SponsorForm(instance=sponsor_record)

    context = {"form_name": "Sponsor Registration", "form": form}
    return render(request, template_name, context)


# =================================== Deleted selected Sponsor ===================================
@login_required
@transaction.atomic
def delete_sponsor(request, pk):
    records = Sponsor.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("sponsor_list"))


# =================================== Depart Sponsor ===================================
@login_required
@transaction.atomic
def sponsor_departure(request):
    if request.method == "POST":
        form = SponsorDepartForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor_id = request.POST.get("id")
            sponsor_instance = get_object_or_404(Sponsor, pk=sponsor_id)

             # Create a sponsorDepart instance
            sponsor_depart = SponsorDeparture.objects.create(sponsor=sponsor_instance)
            sponsor_depart.departure_date = form.cleaned_data["departure_date"]
            sponsor_depart.departure_reason = form.cleaned_data["departure_reason"]
            sponsor_depart.save()

            # Update sponsor status to "departed"
            sponsor_instance.is_departed = "Yes"
            sponsor_instance.save()

            messages.success(request, "Sponsor departed successfully!")
            return redirect("sponsor_departure")
        else:
            messages.error(request, "Form is invalid.")
    else:
        form = SponsorDepartForm()

    sponsors = Sponsor.objects.filter(is_departed="No").order_by("id") 
    return render(
        request,
        "main/sponsor/sponsor_depature.html",
        {"form": form, "form_name": "Sponsors Depature Form", "sponsors": sponsors},
    )

# =================================== sponsor Depature Report ===================================
def sponsor_depature_list(request):
    queryset = Sponsor.objects.all().filter(is_departed="Yes").order_by("id").prefetch_related("departures")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(first_name__icontains=search_query).filter(last_name__icontains=search_query)

    paginator = Paginator(queryset, 25)  # Show 10 records per page
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
        "main/sponsor/sponsor_depature_list.html",
        {"records": records, "table_title": "Departed Sponsors"},
    )

# =================================== Reinstate departed sponsor ===================================
@login_required
@transaction.atomic
def reinstate_sponsor(request, pk):
    sponsor = get_object_or_404(Sponsor, id=pk)
    
    if request.method == 'POST':
        sponsor.is_departed = "No"
        sponsor.save()
        messages.success(request, "Sponsor reinstated successfully!")

        return redirect("depature_list")
    
    return render(request, 'main/sponsor/sponsor_depature_list.html', {'sponsor': sponsor})