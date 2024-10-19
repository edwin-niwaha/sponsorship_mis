from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from openpyxl import load_workbook

from django.core.management import call_command

from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

from .forms import SponsorDepartForm, SponsorForm, SponsorUploadForm
from .models import (
    Sponsor,
    SponsorDeparture,
)

import logging

logger = logging.getLogger(__name__)


# =================================== Sponsors List ===================================
@login_required
@admin_or_manager_or_staff_required
def sponsor_list(request):
    queryset = Sponsor.objects.all().filter(is_departed=False).order_by("id")

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
        "sdms/sponsor/sponsor_details.html",
        {"records": records, "table_title": "Sponsors List"},
    )


# =================================== Register Sponsor ===================================


@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def register_sponsor(request):
    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.info(
                request, "Record saved successfully!", extra_tags="bg-success"
            )
            return redirect("register_sponsor")
        else:
            # Display an error message if the form is not valid
            messages.error(
                request,
                "There was an error saving the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )
    else:
        form = SponsorForm()
    return render(
        request,
        "sdms/sponsor/sponsor_register.html",
        {"form_name": "Sponsor Registration", "form": form},
    )


# =================================== Update Sponsor data ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def update_sponsor(request, pk, template_name="sdms/sponsor/sponsor_register.html"):
    try:
        sponsor_record = Sponsor.objects.get(pk=pk)
    except Sponsor.DoesNotExist:
        messages.error(request, "Record not found!", extra_tags="bg-danger")
        return redirect("sponsor_list")  # Or a relevant error page

    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES, instance=sponsor_record)
        if form.is_valid():
            form.save()

            messages.success(
                request, "Record updated successfully!", extra_tags="bg-success"
            )
            return redirect("sponsor_list")
        else:
            # Display an error message if the form is not valid
            messages.error(
                request,
                "There was an error updating the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )
    else:
        # Pre-populate the form with existing data
        form = SponsorForm(instance=sponsor_record)

    context = {"form_name": "Sponsor Registration", "form": form}
    return render(request, template_name, context)


# =================================== Delete selected Sponsor ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_sponsor(request, pk):
    records = Sponsor.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("sponsor_list"))


# =================================== Depart Sponsor ===================================
@login_required
@admin_or_manager_required
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
            sponsor_instance.is_departed = True
            sponsor_instance.save()

            messages.success(
                request, "Sponsor departed successfully!", extra_tags="bg-success"
            )
            return redirect("sponsor_departure")
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = SponsorDepartForm()

    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/sponsor/sponsor_depature.html",
        {"form": form, "form_name": "Sponsors Depature Form", "sponsors": sponsors},
    )


# =================================== sponsor Depature Report ===================================
@login_required
@admin_or_manager_or_staff_required
def sponsor_depature_list(request):
    queryset = (
        Sponsor.objects.all()
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
        "sdms/sponsor/sponsor_depature_list.html",
        {"records": records, "table_title": "Departed Sponsors"},
    )


# =================================== Reinstate departed sponsor ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def reinstate_sponsor(request, pk):
    sponsor = get_object_or_404(Sponsor, id=pk)

    if request.method == "POST":
        sponsor.is_departed = False
        sponsor.save()
        messages.success(
            request, "Sponsor reinstated successfully!", extra_tags="bg-success"
        )

        return redirect("sponsor_depature_list")

    return render(
        request, "sdms/sponsor/sponsor_depature_list.html", {"sponsor": sponsor}
    )


# =================================== Process and Import Excel data ===================================
@login_required
@admin_required
@transaction.atomic
def import_sponsor_data(request):
    if request.method == "POST":
        form = SponsorUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["excel_file"]
            try:
                # Call process_and_import_data function
                process_and_import_data(excel_file)
                messages.success(
                    request, "Data imported successfully!", extra_tags="bg-success"
                )
            except Exception as e:
                messages.error(
                    request, f"Error importing data: {e}", extra_tags="bg-danger"
                )  # Handle unexpected errors
            return redirect("import_sponsor_data")  # Replace with your redirect URL
    else:
        form = SponsorUploadForm()
    return render(
        request,
        "sdms/sponsor/import_sponsors.html",
        {"form_name": "Import Sponsors - Excel", "form": form},
    )


# Function to import Excel data
def parse_boolean(value):
    """Convert values like 'Yes' or 'No' to boolean."""
    if value in ["Yes", "yes", True]:
        return True
    elif value in ["No", "no", False]:
        return False
    return None


def process_and_import_data(excel_file):
    try:
        wb = load_workbook(excel_file)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2):
            data = {
                "first_name": row[0].value,
                "last_name": row[1].value,
                "gender": row[2].value,
                "email": row[3].value,
                "sponsorship_type": row[4].value,
                "expected_amt": row[5].value,
                "job_title": row[6].value,
                "region": row[7].value,
                "town": row[8].value,
                "origin": row[9].value,
                "business_telephone": row[10].value,
                "mobile_telephone": row[11].value,
                "city": row[12].value,
                "start_date": row[13].value,
                "first_street_address": row[14].value,
                "second_street_address": row[15].value,
                "zip_code": row[16].value,
                "is_departed": parse_boolean(row[17].value),
                "comment": row[18].value,
            }

            # Validate and log data
            logger.debug(f"Processing data: {data}")

            # Ensure values conform to the constraints
            if not data["first_name"]:
                logger.warning(f"Skipping row with missing first_name: {data}")
                continue  # Skip rows with missing required fields

            # Save the record
            obj = Sponsor(**data)
            obj.save()
    except Exception as e:
        logger.error(
            f"Error importing data: {e}", exc_info=True
        )  # Log error with traceback
        raise e


# =================================== Fetch and display imported data ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def imported_sponsors(request):
    records = Sponsor.objects.all().filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/sponsor/imported_sponsors_rpt.html",
        {"table_title": "Imported Sponsors - Excel", "records": records},
    )


# =================================== Delete all sponsors at once ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_sponsors(request):
    if request.method == "POST":
        Sponsor.objects.all().delete()
        messages.info(request, "All records deleted!", extra_tags="bg-danger")
        return HttpResponseRedirect(reverse("imported_sponsors"))


# ===================================  'Update all phone numbers to include a prefix + sign' ===================================
@login_required
@admin_required
def update_sponsor_contacts(request):
    if request.method == "POST":
        # Call the management command and handle success or failure
        try:
            call_command(
                "sponsor_contacts"
            )  # Replace "sponsor_contacts" with your actual command name
            messages.success(
                request,
                "Sponsors contacts updated successfully!",
                extra_tags="bg-success",
            )
            logger.info("Successfully updated sponsors contacts.")
        except Exception as e:
            messages.error(
                request,
                f"Error updating sponsors contacts: {e}",
                extra_tags="bg-danger",
            )
            logger.error(f"Error updating sponsors contacts: {e}", exc_info=True)

        # Redirect to avoid re-posting data on refresh
        return HttpResponseRedirect(reverse("imported_sponsors"))

    # Render the form if not a POST request
    return render(request, "sdms/sponsor/imported_sponsors_rpt.html")
