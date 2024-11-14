from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.child.models import Child
from apps.sponsor.models import Sponsor
from apps.staff.models import Staff
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
)

from .forms import (
    ChildSponsorshipEditForm,
    ChildSponsorshipForm,
    StaffSponsorshipEditForm,
    StaffSponsorshipForm,
)
from .models import (
    ChildSponsorship,
    StaffSponsorship,
)


# =================================== Child Sponsorship ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def child_sponsorship(request):
    if request.method == "POST":
        form = ChildSponsorshipForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor_id = request.POST.get("sponsor_id")
            child_id = request.POST.get("child_id")
            sponsor_instance = get_object_or_404(Sponsor, pk=sponsor_id)
            child_instance = get_object_or_404(Child, pk=child_id)

            # Check if sponsorship already exists
            existing_sponsorship = ChildSponsorship.objects.filter(
                sponsor=sponsor_instance, child=child_instance
            ).exists()
            if existing_sponsorship:
                messages.error(
                    request,
                    "Sponsorship already exists for this child and sponsor.",
                    extra_tags="bg-danger",
                )
            else:
                try:
                    # Create the sponsorship instance
                    with transaction.atomic():
                        sponsorship = ChildSponsorship.objects.create(
                            sponsor=sponsor_instance, child=child_instance
                        )
                        sponsorship.sponsorship_type = form.cleaned_data[
                            "sponsorship_type"
                        ]
                        sponsorship.start_date = form.cleaned_data["start_date"]
                        sponsorship.save()

                        # Update sponsor status to "departed"
                        child_instance.is_sponsored = True
                        child_instance.save()

                    messages.success(
                        request, "Assigned successfully!", extra_tags="bg-success"
                    )
                    return redirect("child_sponsorship")
                except IntegrityError:
                    # Handle integrity error if any
                    messages.error(
                        request, "An error occurred while processing the request."
                    )
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = ChildSponsorshipForm()

    children = Child.objects.filter(is_departed=False).order_by("id")
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/sponsorship/child_sponsorship.html",
        {
            "form": form,
            "form_name": "Child Sponsorship",
            "sponsors": sponsors,
            "children": children,
        },
    )


# =================================== Child Sponsorship Report ===================================
@login_required
@admin_or_manager_or_staff_required
def child_sponsorship_report(request):
    if request.method == "POST":
        child_id = request.POST.get("id")
        if child_id:
            selected_child = get_object_or_404(Child, id=child_id)
            child_sponsorship = ChildSponsorship.objects.filter(child_id=child_id)
            children = Child.objects.all().filter(is_departed=False).order_by("id")
            return render(
                request,
                "sdms/sponsorship/child_sponsorship_rpt.html",
                {
                    "table_title": "child-to-sponsor report",
                    "children": children,
                    "child_name": selected_child.full_name,
                    "prefix_id": selected_child.prefixed_id,
                    "child_sponsorship": child_sponsorship,
                },
            )
        else:
            messages.error(request, "No child selected.", extra_tags="bg-danger")
    else:
        children = Child.objects.all().filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/sponsorship/child_sponsorship_rpt.html",
        {"table_title": "sponsorship report - child", "children": children},
    )


# =================================== sponsor_to_child_rpt ===================================
@login_required
@admin_or_manager_or_staff_required
def sponsor_to_child_rpt(request):
    sponsors = Sponsor.objects.all().filter(is_departed=False).order_by("id")
    if request.method == "POST":
        sponsor_id = request.POST.get("sponsor_id")
        if sponsor_id:
            selected_sponsor = get_object_or_404(Sponsor, id=sponsor_id)
            sponsor_to_child = ChildSponsorship.objects.filter(sponsor_id=sponsor_id)
            return render(
                request,
                "sdms/sponsorship/sponsor_to_child_rpt.html",
                {
                    "table_title": "sponsor-to-child report",
                    "sponsors": sponsors,
                    "first_name": selected_sponsor.first_name,
                    "last_name": selected_sponsor.last_name,
                    "prefix_id": selected_sponsor.prefixed_id,
                    "sponsor_to_child": sponsor_to_child,
                },
            )
        else:
            messages.error(request, "No sponsor selected.", extra_tags="bg-danger")
    return render(
        request,
        "sdms/sponsorship/sponsor_to_child_rpt.html",
        {"table_title": "sponsorship report - sponsor", "sponsors": sponsors},
    )


# =================================== Edit Staff Sponsorship Data ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def edit_child_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(ChildSponsorship, id=sponsorship_id)

    if request.method == "POST":
        form = ChildSponsorshipEditForm(request.POST, instance=sponsorship)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Child sponsorship updated successfully!",
                extra_tags="bg-success",
            )
            return redirect(
                "child_sponsorship_report"
            )  # Redirect to a report or list view
    else:
        form = ChildSponsorshipEditForm(instance=sponsorship)

    return render(
        request,
        "sdms/sponsorship/child_sponsorship_edit.html",
        {
            "form_name": "CHILD SPONSORSHIP UPDATE",
            "form": form,
            "sponsorship": sponsorship,
        },
    )


# =================================== Delete Sponsorship Data ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_child_sponsorship(request, pk):
    records = ChildSponsorship.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("child_sponsorship_report"))


# =================================== Terminate Child Sponsorship ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def terminate_child_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(ChildSponsorship, id=sponsorship_id)

    if request.method == "POST":
        if sponsorship.is_active:
            sponsorship.end_date = timezone.now().date()  # Set end_date to today
            sponsorship.is_active = False
            sponsorship.save()

            # Assuming a direct ForeignKey relationship to Child
            sponsored_child = sponsorship.child
            if sponsored_child:
                sponsored_child.is_sponsored = False
                sponsored_child.save()

            messages.success(
                request, "Sponsorship terminated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("child_sponsorship_report"))

    return HttpResponseBadRequest("Invalid request")


# =================================== Staff Sponsorship ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def staff_sponsorship_create(request):
    if request.method == "POST":
        form = StaffSponsorshipForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor_id = request.POST.get("sponsor_id")
            staff_id = request.POST.get("id")

            sponsor_instance = get_object_or_404(Sponsor, pk=sponsor_id)
            staff_instance = get_object_or_404(Staff, pk=staff_id)

            # Check if sponsorship already exists
            existing_sponsorship = StaffSponsorship.objects.filter(
                sponsor=sponsor_instance, staff=staff_instance
            ).exists()
            if existing_sponsorship:
                messages.error(
                    request, "Sponsorship already exists for this staff and sponsor."
                )
            else:
                try:
                    # Create the sponsorship instance
                    with transaction.atomic():
                        sponsorship = StaffSponsorship.objects.create(
                            sponsor=sponsor_instance, staff=staff_instance
                        )
                        sponsorship.sponsorship_type = form.cleaned_data[
                            "sponsorship_type"
                        ]
                        sponsorship.start_date = form.cleaned_data["start_date"]
                        sponsorship.save()

                        # Update sponsorship status
                        staff_instance.is_sponsored = True
                        staff_instance.save()

                    messages.success(
                        request, "Assigned successfully!", extra_tags="bg-success"
                    )
                    return redirect("staff_sponsorship_create")
                except IntegrityError:
                    # Handle integrity error if any
                    messages.error(
                        request, "An error occurred while processing the request."
                    )
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = StaffSponsorshipForm()

    active_staff = Staff.objects.filter(is_departed=False).order_by("id")
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/sponsorship/staff_sponsorship.html",
        {
            "form": form,
            "form_name": "Staff Sponsorship",
            "sponsors": sponsors,
            "active_staff": active_staff,
        },
    )


# =================================== Staff Sponsorship Report ===================================
@login_required
@admin_or_manager_or_staff_required
def staff_sponsorship_report(request):
    if request.method == "POST":
        staff_id = request.POST.get("id")
        if staff_id:
            selected_staff = get_object_or_404(Staff, id=staff_id)
            staff_sponsorship = StaffSponsorship.objects.filter(staff_id=staff_id)
            active_staff = Staff.objects.all().filter(is_departed=False).order_by("id")
            return render(
                request,
                "sdms/sponsorship/staff_sponsorship_rpt.html",
                {
                    "table_title": "Staff Sponsorship Report",
                    "active_staff": active_staff,
                    "first_name": selected_staff.first_name,
                    "last_name": selected_staff.last_name,
                    "prefix_id": selected_staff.prefixed_id,
                    "staff_sponsorship": staff_sponsorship,
                },
            )
        else:
            messages.error(request, "No Staff selected.", extra_tags="bg-danger")
    else:
        active_staff = Staff.objects.all().filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/sponsorship/staff_sponsorship_rpt.html",
        {"table_title": "sponsorship report - Staff", "active_staff": active_staff},
    )


# =================================== sponsor_to_staff_rpt ===================================
@login_required
@admin_or_manager_or_staff_required
def sponsor_to_staff_rpt(request):
    sponsors = Sponsor.objects.all().filter(is_departed=False).order_by("id")
    if request.method == "POST":
        sponsor_id = request.POST.get("sponsor_id")
        if sponsor_id:
            selected_sponsor = get_object_or_404(Sponsor, id=sponsor_id)
            sponsor_to_staff = StaffSponsorship.objects.filter(sponsor_id=sponsor_id)
            return render(
                request,
                "sdms/sponsorship/sponsor_to_staff_rpt.html",
                {
                    "table_title": "sponsorship report - sponsor",
                    "sponsors": sponsors,
                    "first_name": selected_sponsor.first_name,
                    "last_name": selected_sponsor.last_name,
                    "prefix_id": selected_sponsor.prefixed_id,
                    "sponsor_to_staff": sponsor_to_staff,
                },
            )
        else:
            messages.error(request, "No sponsor selected.", extra_tags="bg-danger")
    return render(
        request,
        "sdms/sponsorship/sponsor_to_staff_rpt.html",
        {"table_title": "sponsorship report - sponsor", "sponsors": sponsors},
    )


# =================================== Edit Staff Sponsorship Data ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def edit_staff_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(StaffSponsorship, id=sponsorship_id)

    if request.method == "POST":
        form = StaffSponsorshipEditForm(request.POST, instance=sponsorship)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Staff sponsorship updated successfully!",
                extra_tags="bg-success",
            )
            return redirect(
                "staff_sponsorship_report"
            )  # Redirect to a report or list view
    else:
        form = StaffSponsorshipEditForm(instance=sponsorship)

    return render(
        request,
        "sdms/sponsorship/staff_sponsorship_edit.html",
        {
            "form_name": "STAFF SPONSORSHIP UPDATE",
            "form": form,
            "sponsorship": sponsorship,
        },
    )


# =================================== Delete Sponsorship Data ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_staff_sponsorship(request, pk):
    records = StaffSponsorship.objects.get(id=pk)
    records.delete()

    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("staff_sponsorship_report"))


# =================================== End Staff Sponsorship Data ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def terminate_staff_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(StaffSponsorship, id=sponsorship_id)

    if request.method == "POST":
        if sponsorship.is_active:
            sponsorship.end_date = timezone.now().date()  # Set end_date to today
            sponsorship.is_active = False
            sponsorship.save()

            # Assuming a direct ForeignKey relationship to Staff
            staff_member = (
                sponsorship.staff
            )  # Replace 'staff' with actual related name if different
            if staff_member:
                staff_member.is_sponsored = False
                staff_member.save()

            messages.success(
                request, "Sponsorship terminated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("staff_sponsorship_report"))

    return HttpResponseBadRequest("Invalid request")
