from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.child.models import Child
from apps.sponsor.models import Donor, Sponsor
from apps.staff.models import Staff
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
)

from .forms import (
    ChildPaymentEditForm,
    ChildPaymentForm,
    DonorPaymentForm,
    StaffPaymentEditForm,
    StaffPaymentForm,
)
from .models import (
    ChildPayments,
    DonorPayment,
    StaffPayments,
)


# =================================== Child Payment ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def child_sponsor_payment(request):
    if request.method == "POST":
        form = ChildPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor_id = request.POST.get("sponsor_id")
            child_id = request.POST.get("child_id")

            sponsor_instance = get_object_or_404(Sponsor, pk=sponsor_id)
            child_instance = get_object_or_404(Child, pk=child_id)

            try:
                # Create the payment instance
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.sponsor = sponsor_instance
                    payment.child = child_instance
                    payment.save()

                messages.success(
                    request, "Payment submitted successfully!", extra_tags="bg-success"
                )
                return redirect("child_sponsor_payment")
            except IntegrityError:
                messages.error(
                    request, "An error occurred while processing the request."
                )
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = ChildPaymentForm()

    children = Child.objects.filter(is_departed=False).order_by("id")
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/finance/child_sponsor_payments.html",
        {
            "form": form,
            "form_name": "Child-Sponsor Payments",
            "sponsors": sponsors,
            "children": children,
        },
    )


# =================================== sponsor_payment_without_child Payment ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def sponsor_payment_without_child(request):
    if request.method == "POST":
        form = ChildPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor_id = request.POST.get("sponsor_id")

            sponsor_instance = get_object_or_404(Sponsor, pk=sponsor_id)

            try:
                # Create the payment instance
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.sponsor = sponsor_instance

                    # Since there is no child, don't set child in the payment
                    payment.child = None

                    payment.save()

                messages.success(
                    request, "Payment submitted successfully!", extra_tags="bg-success"
                )
                return redirect("sponsor_payment_without_child")
            except IntegrityError:
                messages.error(
                    request, "An error occurred while processing the request."
                )
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = ChildPaymentForm()

    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/finance/sponsor_payment_without_child.html",
        {
            "form": form,
            "form_name": "Sponsor Payments (Without Child)",
            "sponsors": sponsors,
        },
    )


# =================================== donor_payment_view Payment ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def donor_payment_view(request):
    if request.method == "POST":
        form = DonorPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            donor_id = request.POST.get("donor_id")
            donor_instance = get_object_or_404(Donor, pk=donor_id)

            try:
                # Create the payment instance, link to donor and save
                donor_payment = form.save(commit=False)
                donor_payment.donor = donor_instance
                donor_payment.save()

                messages.success(
                    request, "Payment submitted successfully!", extra_tags="bg-success"
                )
                return redirect("donor_payment")

            except IntegrityError:
                # Handle database integrity errors
                messages.error(
                    request,
                    "An error occurred while processing the payment.",
                    extra_tags="bg-danger",
                )

        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")

    else:
        form = DonorPaymentForm()

    donors = Donor.objects.all().order_by("id")

    return render(
        request,
        "sdms/finance/donor_payments.html",
        {
            "form": form,
            "form_name": " One time contributions",
            "donors": donors,
        },
    )


# =================================== donor_payment_list_view Payment ===================================
@login_required
@admin_or_manager_or_staff_required
def donor_payment_list_view(request):
    search_query = request.GET.get("search", "").strip()
    donor_payments = DonorPayment.objects.all().order_by("-payment_date")

    # Filter by donor name if search query is provided
    if search_query:
        donor_payments = donor_payments.filter(donor__full_name__icontains=search_query)

    # Pagination
    paginator = Paginator(donor_payments, 50)
    page_number = request.GET.get("page")
    donor_payments = paginator.get_page(page_number)

    return render(
        request,
        "sdms/finance/donor_payments_list.html",
        {"donor_payments": donor_payments, "search_query": search_query},
    )


# =================================== delete_donor_payment Transaction ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_donor_payment_view(request, pk):
    records = DonorPayment.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("donor_payment_list"))


# =================================== Saff Payment ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def staff_sponsor_payment(request):
    if request.method == "POST":
        form = StaffPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor_id = request.POST.get("sponsor_id")
            staff_id = request.POST.get("staff_id")

            sponsor_instance = get_object_or_404(Sponsor, pk=sponsor_id)
            staff_instance = get_object_or_404(Staff, pk=staff_id)

            try:
                # Create the payment instance
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.sponsor = sponsor_instance
                    payment.staff = staff_instance
                    payment.save()

                messages.success(
                    request, "Payment submitted successfully!", extra_tags="bg-success"
                )
                return redirect("staff_sponsor_payment")
            except IntegrityError:
                messages.error(
                    request, "An error occurred while processing the request."
                )
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = StaffPaymentForm()

    active_staff = Staff.objects.filter(is_departed=False).order_by("id")
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "sdms/finance/staff_sponsor_payments.html",
        {
            "form": form,
            "form_name": "Staff-Sponsor Payments",
            "sponsors": sponsors,
            "active_staff": active_staff,
        },
    )


# =================================== Validate Child payment  ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def validate_child_payment(request, payment_id):
    sponsor_payments = get_object_or_404(ChildPayments, id=payment_id)

    if request.method == "POST":
        if not sponsor_payments.is_valid:
            sponsor_payments.is_valid = True
            sponsor_payments.save()

            messages.success(
                request, "Pyament validated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("child_sponsor_payments_report"))

    return HttpResponseBadRequest("Invalid request")


# =================================== Edit Child Payment  ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def edit_child_payment(request, payment_id):
    sponsor_payments = get_object_or_404(ChildPayments, id=payment_id)

    if request.method == "POST":
        form = ChildPaymentEditForm(request.POST, instance=sponsor_payments)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated successfully!", extra_tags="bg-success")
            return redirect("child_sponsor_payments_report")
    else:
        form = ChildPaymentEditForm(instance=sponsor_payments)

    return render(
        request,
        "sdms/finance/child_payment_edit.html",
        {
            "form_name": "PAYEMENT UPDATE",
            "form": form,
            "sponsor_payments": sponsor_payments,
        },
    )


# =================================== Delete Child Payment Transaction ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_child_payment(request, pk):
    records = ChildPayments.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("child_sponsor_payments_report"))


# =================================== Validate Staff payment  ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def validate_staff_payment(request, payment_id):
    sponsor_payments = get_object_or_404(StaffPayments, id=payment_id)

    if request.method == "POST":
        if not sponsor_payments.is_valid:
            sponsor_payments.is_valid = True
            sponsor_payments.save()

            messages.success(
                request, "Pyament validated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("staff_sponsor_payments_report"))

    return HttpResponseBadRequest("Invalid request")


# =================================== Edit Staff Payment  ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def edit_staff_payment(request, payment_id):
    sponsor_payments = get_object_or_404(StaffPayments, id=payment_id)

    if request.method == "POST":
        form = StaffPaymentEditForm(request.POST, instance=sponsor_payments)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated successfully!", extra_tags="bg-success")
            return redirect("staff_sponsor_payments_report")
    else:
        form = ChildPaymentEditForm(instance=sponsor_payments)

    return render(
        request,
        "sdms/finance/staff_payment_edit.html",
        {
            "form_name": "PAYEMENT UPDATE",
            "form": form,
            "sponsor_payments": sponsor_payments,
        },
    )


# =================================== Delete Staff Payment Transaction ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_staff_payment(request, pk):
    records = StaffPayments.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("staff_sponsor_payments_report"))


# =================================== Child & Saff Payments Reports ===================================


def group_payments_by_year(payments):
    payments_by_year = defaultdict(list)
    for payment in payments:
        payments_by_year[payment.payment_year].append(payment)
    return payments_by_year


def calculate_subtotals(payments_by_year):
    return {
        year: sum(p.amount for p in payments)
        for year, payments in payments_by_year.items()
    }


def generate_payments_report(request, report_title, template_name, payment_model):
    sponsors = Sponsor.objects.all().order_by("id")
    context = {
        "table_title": report_title,
        "sponsors": sponsors,
    }

    if request.method == "POST":
        sponsor_id = request.POST.get("id")
        if sponsor_id:
            selected_sponsor = get_object_or_404(Sponsor, id=sponsor_id)
            sponsor_payments = payment_model.objects.filter(
                sponsor_id=sponsor_id
            ).order_by("-payment_year")

            # Group payments by year and calculate subtotals
            payments_by_year = group_payments_by_year(sponsor_payments)
            subtotals = calculate_subtotals(payments_by_year)
            total_amount = sum(subtotals.values())

            context.update(
                {
                    "first_name": selected_sponsor.first_name,
                    "last_name": selected_sponsor.last_name,
                    "prefix_id": selected_sponsor.prefixed_id,
                    "sponsor_payments": sponsor_payments,
                    "total_amount": total_amount,
                    "payments_by_year": payments_by_year,
                    "subtotals": subtotals,
                }
            )

            return render(request, template_name, context)
        else:
            messages.error(request, "No Sponsor selected.", extra_tags="bg-danger")

    return render(request, template_name, context)


@login_required
@admin_or_manager_or_staff_required
def child_sponsor_payments_report(request):
    return generate_payments_report(
        request,
        "Child - Sponsor Payments Report",
        "sdms/finance/child_sponsor_payments_rpt.html",
        ChildPayments,
    )


@login_required
@admin_or_manager_or_staff_required
def staff_sponsor_payments_report(request):
    return generate_payments_report(
        request,
        "Staff - Sponsor Payments Report",
        "sdms/finance/staff_sponsor_payments_rpt.html",
        StaffPayments,
    )
