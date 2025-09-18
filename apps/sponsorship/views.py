import json
import requests
import uuid
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from base64 import b64encode
from django import forms
from .models import Donor, Donation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
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
    DonationForm,
)
from .models import (
    ChildSponsorship,
    Donation, 
    Donor,
    StaffSponsorship,
)

# Set up logging
logger = logging.getLogger(__name__)

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
        "sponsorship/child_sponsorship.html",
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
                "sponsorship/child_sponsorship_rpt.html",
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
        "sponsorship/child_sponsorship_rpt.html",
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
                "sponsorship/sponsor_to_child_rpt.html",
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
        "sponsorship/sponsor_to_child_rpt.html",
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
        "sponsorship/child_sponsorship_edit.html",
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
        "sponsorship/staff_sponsorship.html",
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
                "sponsorship/staff_sponsorship_rpt.html",
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
        "sponsorship/staff_sponsorship_rpt.html",
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
                "sponsorship/sponsor_to_staff_rpt.html",
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
        "sponsorship/sponsor_to_staff_rpt.html",
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
        "sponsorship/staff_sponsorship_edit.html",
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


# =================================== payment_flutter_view ===================================
# @login_required
# @csrf_exempt
# def initiate_payment(request):
#     if request.method == "POST":
#         total_amount = request.POST.get("total_amount")
#         email = request.POST.get("email")

#         if not total_amount or not email:
#             return render(
#                 request,
#                 "sponsorship/payment_flutter.html",
#                 {"error": "Please provide both email and amount."},
#             )

#         try:
#             total_amount = float(total_amount)
#             if total_amount <= 0:
#                 raise ValueError("Amount must be positive")
#         except ValueError:
#             return render(
#                 request,
#                 "sponsorship/payment_flutter.html",
#                 {"error": "Invalid amount. Please enter a valid number."},
#             )

#         reference = str(uuid.uuid4())
#         user = request.user

#         flutterwave_url = "https://api.flutterwave.com/v3/payments"
#         secret_key = settings.FLUTTERWAVE_SECRET_KEY

#         payload = {
#             "tx_ref": reference,
#             "amount": total_amount,
#             "currency": "UGX",
#             "redirect_url": "http://127.0.0.1:8000/payment/callback",
#             "payment_options": "card,mobilemoneyghana,mpesa,ussd",
#             "customer": {"email": email},
#         }

#         headers = {
#             "Authorization": f"Bearer {secret_key}",
#             "Content-Type": "application/json",
#         }

#         try:
#             payment = Payment(
#                 user=user,
#                 email=email,
#                 total_amount=total_amount,
#                 reference=reference,
#                 status="pending",
#             )
#             payment.save()

#             response = requests.post(flutterwave_url, json=payload, headers=headers)
#             response_data = response.json()

#             if response_data.get("status") == "success" and response_data.get(
#                 "data", {}
#             ).get("link"):
#                 return HttpResponseRedirect(
#                     response_data["data"]["link"]
#                 )  # Redirect to Flutterwave payment link
#             else:
#                 payment.status = "failed"
#                 payment.save()
#                 return render(
#                     request,
#                     "sponsorship/payment_flutter.html",
#                     {"error": "Payment initiation failed. Please try again."},
#                 )

#         except requests.exceptions.RequestException:
#             return render(
#                 request,
#                 "sponsorship/payment_flutter.html",
#                 {"error": "Payment initiation failed due to a network error."},
#             )
#         except ValueError:
#             return render(
#                 request,
#                 "sponsorship/payment_flutter.html",
#                 {"error": "Payment initiation failed due to invalid response."},
#             )

#     elif request.method == "GET":
#         return render(request, "sponsorship/payment_flutter.html")

#     return JsonResponse({"error": "Method not allowed"}, status=405)

# def payment_callback(request):
#     if request.method == "GET":
#         status = request.GET.get("status")
#         tx_ref = request.GET.get("tx_ref")

#         if status == "successful":
#             try:
#                 payment = Payment.objects.get(reference=tx_ref)
#                 payment.status = "successful"
#                 payment.save()
#                 return render(
#                     request,
#                     "sponsorship/payment_success.html",
#                     {"message": "Payment was successful!"},
#                 )

#             except Payment.DoesNotExist:
#                 return render(
#                     request,
#                     "sponsorship/payment_flutter.html",
#                     {"error": "Payment not found."},
#                 )

#         return render(
#             request,
#             "sponsorship/payment_flutter.html",
#             {"error": "Payment failed."},
#         )

#     return JsonResponse({"error": "Method not allowed"}, status=405)

# =================================== donation_form ===================================

# ------------------------
# Generate OAuth Token
# ------------------------
def get_momo_token():
    """
    Generate OAuth token for MTN MoMo API (Collection) – supports sandbox and live.
    """
    url = f"https://{settings.MTN_ENVIRONMENT}.momodeveloper.mtn.com/collection/token/"
    # https://sandbox.momodeveloper.mtn.com/collection/token/

    # Basic Auth using API_USER and API_KEY
    auth_string = f"{settings.MTN_API_USER}:{settings.MTN_API_KEY}"
    b64_auth = b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            logger.error(f"Token response missing access_token: {response.text}")
        return token
    except requests.RequestException as e:
        logger.error(f"Token generation failed: {e} | {getattr(e.response, 'text', '')}")
        return None

# ------------------------
# Donation Form View
# ------------------------
def donation_form(request):
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            phone_number = form.cleaned_data['phone_number']
            amount = form.cleaned_data['amount']

            try:
                donor, created = Donor.objects.get_or_create(
                    phone_number=phone_number,
                    defaults={'name': name}
                )

                donation = Donation.objects.create(
                    donor=donor,
                    amount=amount,
                    momo_reference_id=uuid.uuid4(),  # Unique reference
                    status="pending",
                )

                return redirect('initiate_payment', donation_id=donation.id)

            except Exception as e:
                logger.error(f"Donation creation failed: {e}")
                form.add_error(None, "Failed to process donation. Please try again.")

        return render(request, 'sponsorship/donation_form.html', {'form': form})

    return render(request, 'sponsorship/donation_form.html', {'form': DonationForm()})

# ------------------------
# Initiate Payment
# ------------------------
def initiate_payment(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)

    if donation.status != 'pending':
        return JsonResponse({'error': 'Payment already processed'}, status=400)

    token = get_momo_token()
    if not token:
        donation.status = 'failed'
        donation.save()
        return JsonResponse({'error': 'Failed to authenticate with MoMo API'}, status=500)

    url = f"https://{settings.MTN_ENVIRONMENT}.momodeveloper.mtn.com/collection/v1_0/requesttopay"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Reference-Id": str(donation.momo_reference_id),
        "X-Target-Environment": settings.MTN_ENVIRONMENT,  # 'sandbox' or 'live'
        # "X-Callback-Url": settings.MTN_CALLBACK_URL,
        "X-Callback-Url": "https://webhook.site/f35306b9-033c-4fec-b855-a269b26e543a",
        "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "amount": str(donation.amount),
        "currency": "EUR" if settings.MTN_ENVIRONMENT=="sandbox" else "UGX",
        "externalId": str(donation.momo_reference_id),
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": str(donation.donor.phone_number),
        },
        "payerMessage": "Donation Payment",
        "payeeNote": "Thank you for your donation",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 202]:
            donation.transaction_id = donation.momo_reference_id
            donation.save()
            return JsonResponse({'message': 'Payment request sent. Awaiting confirmation.'})
        else:
            donation.status = 'failed'
            donation.save()
            logger.error(f"Payment initiation failed for donation {donation_id}: {response.text}")
            return JsonResponse({'error': f'Payment initiation failed: {response.text}'}, status=400)

    except requests.RequestException as e:
        donation.status = 'failed'
        donation.save()
        logger.error(f"Payment request failed for donation {donation_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ------------------------
# MoMo Callback Handler
# ------------------------
@csrf_exempt
def momo_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        reference_id = data.get('externalId')
        transaction_id = data.get('financialTransactionId')
        status = data.get('status')

        if not all([reference_id, transaction_id, status]):
            return JsonResponse({'error': 'Invalid callback data'}, status=400)

        try:
            donation = Donation.objects.get(momo_reference_id=reference_id)
        except Donation.DoesNotExist:
            return JsonResponse({'error': 'Donation not found'}, status=404)

        if status == 'SUCCESSFUL':
            donation.status = 'completed'
            donation.transaction_id = transaction_id
        elif status in ['FAILED', 'REJECTED']:
            donation.status = 'failed'
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)

        donation.save()
        return JsonResponse({'message': 'Callback processed'})

    return JsonResponse({'error': 'Invalid request'}, status=400)
