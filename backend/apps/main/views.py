import json
# from formtools.wizard.views import SessionWizardView
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from django.db.models import Prefetch
from django.db import transaction

from .models import *
from .forms import *

def home(request):
    return render(request, "users/home.html")


@login_required
def dashboard(request):
    c_records = ChildProfile.objects.all()
    total_records = c_records.count()

    context = {
        "kids_registered": total_records,
        "total_no_of_kids": total_records,
    }
    return render(request, "main/dashboard.html", context)


@login_required
def child_list(request):
    c_records = ChildProfile.objects.all()
    return render(request, 'main/child/manage_child.html', {'c_records': c_records})
@login_required
def child_details(request, pk):
    record = ChildProfile.objects.get(pk=pk)
    context = {'record': record}
    return render(request, 'main/child/child_profile_rpt.html', context)

@login_required
@transaction.atomic
def register_child(request):
  if request.method == 'POST':
    form = ChildDetailsForm(request.POST, request.FILES)

    if form.is_valid(): 
      form.save()
      messages.info(request, "Record saved successfully!", extra_tags="bg-success")

    else:
      # Display form errors
      return render(request, 'main/child/child_frm.html', {'form': form})
  else:
    form = ChildDetailsForm()
  return render(request, 'main/child/child_frm.html', {'form': form})


# @login_required
# def update_child(request, pk, template_name="main/child/child_frm.html"):
#     c_record = get_object_or_404(ChildProfile, id=pk)
#     form = ChildDetailsForm(request.POST or None, instance=c_record)
#     if form.is_valid():
#         form.save()
#         messages.info(request, "Record updated successfully!", extra_tags="bg-success")
#         return redirect("child_list")
#     return render(request, template_name, {"form": form})

@login_required
def update_child(request, pk, template_name="main/child/child_frm.html"):
    try:
        c_record = ChildProfile.objects.get(pk=pk)
    except ChildProfile.DoesNotExist:
        messages.error(request, "Child record not found!", extra_tags="bg-danger")
        return redirect("child_list")  # Or a relevant error page

    # Update the form to handle pictures (assuming ChildDetailsForm)
    form = ChildDetailsForm(request.POST or None, request.FILES or None, instance=c_record)

    if form.is_valid():
        form.save()  # This will save the updated picture if uploaded
        messages.info(request, "Record updated successfully!", extra_tags="bg-success")
        return redirect("child_list")  # Replace with the appropriate redirect URL

    context = {'form': form, 'child': c_record}  # Include child record for display (optional)
    return render(request, template_name, context)

@login_required
@transaction.atomic
def delete_child(request, pk):
    c_records = ChildProfile.objects.get(id=pk)
    c_records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")

    return HttpResponseRedirect(reverse("child_list"))