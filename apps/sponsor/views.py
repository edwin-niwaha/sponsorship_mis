from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.child.models import Child
from apps.staff.models import Staff

from .forms import (
    ChildSponsorshipForm,
    ChildSponsorshipEditForm,
    SponsorDepartForm,
    SponsorForm,
    StaffSponsorshipEditForm,
    StaffSponsorshipForm,
)
from .models import (
    ChildSponsorship,
    Sponsor,
    SponsorDeparture,
    StaffSponsorship,
)


# =================================== Sponsors List ===================================
@login_required
def sponsor_list(request):
    queryset = Sponsor.objects.all().filter(is_departed=False).order_by("id")

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
            return redirect("register_sponsor") 
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
            return redirect("sponsor_list") 
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
            sponsor_instance.is_departed = True
            sponsor_instance.save()

            messages.success(request, "Sponsor departed successfully!")
            return redirect("sponsor_departure")
        else:
            messages.error(request, "Form is invalid.")
    else:
        form = SponsorDepartForm()

    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id") 
    return render(
        request,
        "main/sponsor/sponsor_depature.html",
        {"form": form, "form_name": "Sponsors Depature Form", "sponsors": sponsors},
    )

# =================================== sponsor Depature Report ===================================
def sponsor_depature_list(request):
    queryset = Sponsor.objects.all().filter(is_departed=True).order_by("id").prefetch_related("departures")

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
        sponsor.is_departed = False
        sponsor.save()
        messages.success(request, "Sponsor reinstated successfully!")

        return redirect("sponsor_depature_list")
    
    return render(request, 'main/sponsor/sponsor_depature_list.html', {'sponsor': sponsor})


# =================================== Child Sponsorship ===================================
@login_required
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
                sponsor=sponsor_instance, 
                child=child_instance).exists()
            if existing_sponsorship:
                messages.error(request, "Sponsorship already exists for this child and sponsor.")
            else:
                try:
                    # Create the sponsorship instance
                    with transaction.atomic():
                        sponsorship = ChildSponsorship.objects.create(sponsor=sponsor_instance, child=child_instance)
                        sponsorship.sponsorship_type = form.cleaned_data["sponsorship_type"]
                        sponsorship.start_date = form.cleaned_data["start_date"]
                        sponsorship.save()

                        # Update sponsor status to "departed"
                        child_instance.is_sponsored = True
                        child_instance.save()

                    messages.success(request, "Assigned successfully!")
                    return redirect("child_sponsorship")
                except IntegrityError:
                    # Handle integrity error if any
                    messages.error(request, "An error occurred while processing the request.")
        else:
            messages.error(request, "Form is invalid.")
    else:
        form = ChildSponsorshipForm()

    children = Child.objects.filter(is_departed=False).order_by("id")  
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id") 
    return render(
        request,
        "main/sponsorship/child_sponsorship.html",
        {"form": form, "form_name": "Child Sponsorship", "sponsors": sponsors, "children": children},
    )

# =================================== Child Sponsorship Report ===================================
@login_required
def child_sponsorship_report(request):
    if request.method == "POST":
        child_id = request.POST.get("id")
        if child_id:
            selected_child = get_object_or_404(Child, id=child_id)
            child_sponsorship = ChildSponsorship.objects.filter(child_id=child_id)
            children = Child.objects.all().filter(is_departed=False).order_by("id")
            return render(request, 'main/sponsorship/child_sponsorship_rpt.html', 
                          {"table_title": "Child Sponsorship Report", "children": children, 
                           "child_name": selected_child.full_name, "prefix_id":selected_child.prefixed_id, 
                           'child_sponsorship': child_sponsorship})
        else:
            messages.error(request, "No child selected.")
    else:
        children = Child.objects.all().filter(is_departed=False).order_by("id")
    return render(request, 'main/sponsorship/child_sponsorship_rpt.html', 
                    {"table_title": "Child Sponsorship Report", "children": children})

# =================================== Edit Staff Sponsorship Data ===================================
@login_required
@transaction.atomic
def edit_child_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(ChildSponsorship, id=sponsorship_id)

    if request.method == 'POST':
        form = ChildSponsorshipEditForm(request.POST, instance=sponsorship)
        if form.is_valid():
            form.save()
            messages.success(request, 'Child sponsorship updated successfully!')
            return redirect('child_sponsorship_report')  # Redirect to a report or list view
    else:
        form = ChildSponsorshipEditForm(instance=sponsorship)

    return render(request, 'main/sponsorship/child_sponsorship_edit.html', {'form_name': 'CHILD SPONSORSHIP UPDATE', 'form': form, 'sponsorship': sponsorship})


# =================================== Delete Sponsorship Data ===================================
@login_required
@transaction.atomic
def delete_child_sponsorship(request, pk):
    records = ChildSponsorship.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("child_sponsorship_report"))

# =================================== Terminate Child Sponsorship ===================================
@login_required
@transaction.atomic
def terminate_child_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(ChildSponsorship, id=sponsorship_id)

    if request.method == 'POST':
        if sponsorship.is_active:
            sponsorship.end_date = timezone.now().date()  # Set end_date to today
            sponsorship.is_active = False
            sponsorship.save()

            # Assuming a direct ForeignKey relationship to Child
            sponsored_child = sponsorship.child  
            if sponsored_child:
                sponsored_child.is_sponsored = False
                sponsored_child.save()

            messages.success(request, "Sponsorship terminated successfully!")
            return HttpResponseRedirect(reverse("child_sponsorship_report"))

    return HttpResponseBadRequest('Invalid request')


# =================================== Staff Sponsorship ===================================
@login_required
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
                sponsor=sponsor_instance, 
                staff=staff_instance).exists()
            if existing_sponsorship:
                messages.error(request, "Sponsorship already exists for this staff and sponsor.")
            else:
                try:
                    # Create the sponsorship instance
                    with transaction.atomic():
                        sponsorship = StaffSponsorship.objects.create(sponsor=sponsor_instance, staff=staff_instance)
                        sponsorship.sponsorship_type = form.cleaned_data["sponsorship_type"]
                        sponsorship.start_date = form.cleaned_data["start_date"]
                        sponsorship.save()

                        # Update sponsorship status
                        staff_instance.is_sponsored = True
                        staff_instance.save()

                    messages.success(request, "Assigned successfully!")
                    return redirect("staff_sponsorship_create")
                except IntegrityError:
                    # Handle integrity error if any
                    messages.error(request, "An error occurred while processing the request.")
        else:
            messages.error(request, "Form is invalid.")
    else:
        form = StaffSponsorshipForm()

    active_staff = Staff.objects.filter(is_departed=False).order_by("id")  
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id") 
    return render(
        request,
        "main/sponsorship/staff_sponsorship.html",
        {"form": form, "form_name": "Staff Sponsorship", "sponsors": sponsors, "active_staff": active_staff},
    )

# =================================== Staff Sponsorship Report ===================================
@login_required
def staff_sponsorship_report(request):
    if request.method == "POST":
        staff_id = request.POST.get("id")
        if staff_id:
            selected_staff = get_object_or_404(Staff, id=staff_id)
            staff_sponsorship = StaffSponsorship.objects.filter(staff_id=staff_id)
            active_staff = Staff.objects.all().filter(is_departed=False).order_by("id")
            return render(request, 'main/sponsorship/staff_sponsorship_rpt.html', 
                          {"table_title": "Staff Sponsorship Report", 
                           "active_staff": active_staff, 
                           "first_name": selected_staff.first_name, 
                           "last_name": selected_staff.last_name,
                           "prefix_id":selected_staff.prefixed_id, 
                           'staff_sponsorship': staff_sponsorship})
        else:
            messages.error(request, "No Staff selected.")
    else:
        active_staff = Staff.objects.all().filter(is_departed=False).order_by("id")
    return render(request, 'main/sponsorship/staff_sponsorship_rpt.html', 
                    {"table_title": "Staff Sponsorship Report", "active_staff": active_staff})


# =================================== Edit Staff Sponsorship Data ===================================
@login_required
@transaction.atomic
def edit_staff_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(StaffSponsorship, id=sponsorship_id)

    if request.method == 'POST':
        form = StaffSponsorshipEditForm(request.POST, instance=sponsorship)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff sponsorship updated successfully!')
            return redirect('staff_sponsorship_report')  # Redirect to a report or list view
    else:
        form = StaffSponsorshipEditForm(instance=sponsorship)

    return render(request, 'main/sponsorship/staff_sponsorship_edit.html', {'form_name': 'STAFF SPONSORSHIP UPDATE', 'form': form, 'sponsorship': sponsorship})

# =================================== Delete Sponsorship Data ===================================
@login_required
@transaction.atomic
def delete_staff_sponsorship(request, pk):
    records = StaffSponsorship.objects.get(id=pk)
    records.delete()

    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("staff_sponsorship_report"))

# =================================== End Staff Sponsorship Data ===================================
@login_required
@transaction.atomic
def terminate_staff_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(StaffSponsorship, id=sponsorship_id)

    if request.method == 'POST':
        if sponsorship.is_active:
            sponsorship.end_date = timezone.now().date()  # Set end_date to today
            sponsorship.is_active = False
            sponsorship.save()

            # Assuming a direct ForeignKey relationship to Staff
            staff_member = sponsorship.staff  # Replace 'staff' with actual related name if different
            if staff_member:
                staff_member.is_sponsored = False
                staff_member.save()

            messages.success(request, "Sponsorship terminated successfully!")
            return HttpResponseRedirect(reverse("staff_sponsorship_report"))

    return HttpResponseBadRequest('Invalid request')