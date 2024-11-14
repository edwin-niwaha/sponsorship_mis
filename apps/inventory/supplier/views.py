from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_required,
)

from .forms import SupplierForm
from .models import Supplier


# =================================== supplier list view ===================================
@login_required
@admin_or_manager_or_staff_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(
        request, "inventory/supplier/suppliers.html", {"suppliers": suppliers}
    )


# =================================== supplier add view ===================================
@login_required
@admin_or_manager_or_staff_required
def supplier_add(request):
    form_title = "Add New Supplier"
    form = SupplierForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            supplier = form.save()
            messages.success(
                request,
                f'Supplier "{supplier.name}" added successfully.',
                extra_tags="bg-success",
            )
            return redirect("supplier:supplier_list")

    return render(
        request,
        "inventory/supplier/supplier_add.html",
        {"form": form, "form_title": form_title},
    )


# =================================== supplier update view ===================================
@login_required
@admin_or_manager_or_staff_required
def supplier_update(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    form_title = "Update Supplier"
    form = SupplierForm(request.POST or None, instance=supplier)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
            messages.success(
                request, "Supplier updated successfully!", extra_tags="bg-success"
            )
            return redirect("supplier:supplier_list")

    return render(
        request,
        "inventory/supplier/supplier_update.html",
        {"form": form, "form_title": form_title},
    )


# =================================== supplier delete view ===================================
@login_required
@admin_required
def supplier_delete(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    try:
        supplier.delete()
        messages.success(
            request, f"Supplier: {supplier.name} deleted!", extra_tags="bg-danger"
        )
    except Exception as e:
        messages.error(
            request, "There was an error during the deletion!", extra_tags="bg-danger"
        )
        print(e)

    return redirect("supplier:supplier_list")
