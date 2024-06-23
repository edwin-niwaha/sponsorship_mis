from django.contrib import messages
from django.db.models import Sum
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.child.models import Child
from apps.staff.models import Staff
from apps.sponsor.models import Sponsor

from .forms import (
    ChildPaymentForm,
    ChildPaymentEditForm,
)
from .models import (
    ChildPayments,
)

# =================================== Child Payment ===================================
@login_required
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

                messages.success(request, "Payment submitted successfully!")
                return redirect("child_sponsor_payment")
            except IntegrityError:
                messages.error(request, "An error occurred while processing the request.")
        else:
            messages.error(request, "Form is invalid.")
    else:
        form = ChildPaymentForm()

    children = Child.objects.filter(is_departed=False).order_by("id")
    sponsors = Sponsor.objects.filter(is_departed=False).order_by("id")
    return render(
        request,
        "main/finance/child_sponsor_payments.html",
        {"form": form, "form_name": "Child-Sponsor Payments", "sponsors": sponsors, "children": children},
    )

# =================================== Child Payment Report ===================================

@login_required
def child_sponsor_payments_report(request):
    sponsors = Sponsor.objects.all().order_by("id")
    context = {
        "table_title": "Sponsor Payments Report",
        "sponsors": sponsors,
    }
    
    if request.method == "POST":
        sponsor_id = request.POST.get("id")
        if sponsor_id:
            selected_sponsor = get_object_or_404(Sponsor, id=sponsor_id)
            sponsor_payments = ChildPayments.objects.filter(sponsor_id=sponsor_id).order_by('-payment_year')
            
            # Group payments by year and calculate subtotals
            payments_by_year = group_payments_by_year(sponsor_payments)
            subtotals = calculate_subtotals(payments_by_year)
            total_amount = sum(subtotals.values())
            
            context.update({
                "first_name": selected_sponsor.first_name,
                "last_name": selected_sponsor.last_name,
                "prefix_id": selected_sponsor.prefixed_id,
                "sponsor_payments": sponsor_payments,
                "total_amount": total_amount,
                "payments_by_year": payments_by_year,
                "subtotals": subtotals,
            })
            
            return render(request, 'main/finance/child_sponsor_payments_rpt.html', context)
        else:
            messages.error(request, "No Sponsor selected.")
    
    return render(request, 'main/finance/child_sponsor_payments_rpt.html', context)

def group_payments_by_year(sponsor_payments):
    payments_by_year = defaultdict(list)
    for payment in sponsor_payments:
        payments_by_year[payment.payment_year].append(payment)
    return payments_by_year

def calculate_subtotals(payments_by_year):
    return {year: sum(p.amount for p in payments) for year, payments in payments_by_year.items()}


# =================================== Validate Child payment  ===================================
@login_required
@transaction.atomic
def validate_child_payment(request, payment_id):
    sponsor_payments = get_object_or_404(ChildPayments, id=payment_id)

    if request.method == 'POST':
        if not sponsor_payments.is_valid:
            sponsor_payments.is_valid = True
            sponsor_payments.save()

            messages.success(request, "Pyament validated successfully!")
            return HttpResponseRedirect(reverse("child_sponsor_payments_report"))

    return HttpResponseBadRequest('Invalid request')


# =================================== Edit Child Payment  ===================================
@login_required
@transaction.atomic
def edit_child_payment(request, payment_id):
    sponsor_payments = get_object_or_404(ChildPayments, id=payment_id)

    if request.method == 'POST':
        form = ChildPaymentEditForm(request.POST, instance=sponsor_payments)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated successfully!')
            return redirect('child_sponsor_payments_report')
    else:
        form = ChildPaymentEditForm(instance=sponsor_payments)

    return render(request, 'main/finance/child_payment_edit.html', {'form_name': 'PAYEMENT UPDATE', 'form': form, 'sponsor_payments': sponsor_payments})

# =================================== Delete Child Payment Transaction ===================================
@login_required
@transaction.atomic
def delete_child_payment(request, pk):
    records = ChildPayments.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("child_sponsor_payments_report"))