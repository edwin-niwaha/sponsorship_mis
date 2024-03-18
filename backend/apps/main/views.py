# from formtools.wizard.views import SessionWizardView
from django.http import  HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from openpyxl import load_workbook


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
  return render(request, 'main/child/child_frm.html', {'form_name':'Child Registration', 'form': form})


@login_required
@transaction.atomic
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
    
    context = {'form_name':'Child Registration', 'form': form, 'child': c_record}  # Include child record for display (optional)
    return render(request, template_name, context)

@login_required
@transaction.atomic
def delete_child(request, pk):
    c_records = ChildProfile.objects.get(id=pk)
    c_records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("child_list"))

@login_required
@transaction.atomic
# debug and refactor this code
def import_data(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                # Call process_and_import_data function
                process_and_import_data(excel_file)
                messages.success(request, "Data imported successfully!", extra_tags="bg-success")
            except Exception as e:
                messages.error(request, f"Error importing data: {e}", extra_tags="bg-danger")  # Handle unexpected errors
            return redirect("data_list")  # Replace with your redirect URL
    else:
        form = UploadForm()
    return render(request, 'main/child/import_frm.html', {'form_name': 'Import Excel Data', 'form': form})


# Function to import Excel data
def process_and_import_data(excel_file):
    try:
        wb = load_workbook(excel_file)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2):
            fname = row[0].value

            if fname is not None:
                obj = ExcelImport.objects.create(name=fname)
                obj.save()
    except Exception as e:
        raise e  # Reraise the exception for better error handling at the view level

# view imported data
@login_required
def import_details(request):
    records = ExcelImport.objects.all()
    return render(request, 'main/child/data_list.html', {'records': records})

# delete individual one record at a time
@login_required
@transaction.atomic
def delete_excel_data(request, pk):
    record_imported = ExcelImport.objects.get(id=pk)
    record_imported.delete()
    messages.info(request, "Record deleted!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("data_list"))

# delete all records at once
@login_required
@transaction.atomic
def delete_confirmation(request):
    if request.method == 'POST':
        ExcelImport.objects.all().delete()
        messages.info(request, "All records deleted!", extra_tags="bg-danger")
        return redirect('data_list')  
    return render(request, 'delete_confirmation.html')