import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from xhtml2pdf import pisa

from apps.inventory.customers.models import Customer
from apps.inventory.products.models import Product

# Import custom decorators
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_required,
)
from core.wsgi import *

from .forms import ReportPeriodForm
from .models import Sale, SaleDetail

logger = logging.getLogger(__name__)


# =================================== Sale list view ===================================
@login_required
@admin_or_manager_or_staff_required
def sales_list_view(request):
    # Fetch all sales, including customer and product inventory details
    sales = (
        Sale.objects.all()
        .select_related("customer")
        .prefetch_related("items__product__inventory")
        .order_by("id")
    )

    # Add pagination
    paginator = Paginator(sales, 25)  # Show 10 sales per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate grand total for all sales
    grand_total = sales.aggregate(Sum("grand_total"))["grand_total__sum"] or 0

    # Calculate total items sold across all sales
    total_items = sum(sale.sum_items() for sale in sales)

    # Initialize totals for profit and stock balance
    total_profit = 0
    sales_with_details = []

    # Iterate over each sale to calculate profit
    for sale in sales:
        sale_profit = sum(item.calculate_profit() for item in sale.items.all())
        sale.profit = sale_profit  # Attach calculated profit to sale instance
        total_profit += sale_profit

        # Add the sale to the list with details
        sales_with_details.append(sale)

    # Context to pass to the template
    context = {
        "table_title": "Sales List",  # Title for the table
        "sales": page_obj,  # Paginated sales
        "grand_total": grand_total,  # Total grand total for all sales
        "total_items": total_items,  # Total number of items sold across all sales
        "total_profit": total_profit,  # Total profit from all sales
    }

    return render(request, "inventory/sales/sales.html", context=context)


# =================================== Sale add view ===================================
@admin_or_manager_or_staff_required
@login_required
def sales_add_view(request):
    # Fetch only active products with their inventory
    products = Product.objects.filter(status="ACTIVE").select_related("inventory")

    context = {
        "customers": [c.to_select2() for c in Customer.objects.all()],
        "products": products,
        "total_stock": sum(
            product.inventory.quantity if hasattr(product, "inventory") else 0
            for product in products
        ),
    }

    if request.method == "POST":
        try:
            logger.debug(f"POST data: {request.POST}")

            # Extract and process form data
            customer_id = int(request.POST.get("customer"))
            sale_attributes = {
                "customer": Customer.objects.get(id=customer_id),
                "trans_date": request.POST.get("trans_date"),
                "sub_total": float(request.POST.get("sub_total", 0)),
                "grand_total": float(request.POST.get("grand_total", 0)),
                "tax_amount": float(request.POST.get("tax_amount", 0)),
                "tax_percentage": float(request.POST.get("tax_percentage", 0)),
                "amount_payed": float(request.POST.get("amount_payed", 0)),
                "amount_change": float(request.POST.get("amount_change", 0)),
            }

            with transaction.atomic():
                # Create the sale
                new_sale = Sale.objects.create(**sale_attributes)
                logger.info(f"Sale created successfully: {sale_attributes}")

                # Extract product details from form data
                products_data = request.POST.getlist("products")
                for product_data_str in products_data:
                    product_data = json.loads(product_data_str)
                    product_obj = Product.objects.get(id=int(product_data["id"]))
                    quantity_requested = int(product_data["quantity"])

                    # Check if the product has inventory and stock is available
                    if (
                        not hasattr(product_obj, "inventory")
                        or product_obj.inventory.quantity < quantity_requested
                    ):
                        raise ValueError(
                            f"Oops! Insufficient stock for {product_obj.name}"
                        )

                    # Update inventory stock
                    inventory_obj = product_obj.inventory
                    inventory_obj.quantity -= quantity_requested
                    inventory_obj.save()
                    logger.info(
                        f"Stock updated for {product_obj.name}: {inventory_obj.quantity}"
                    )

                    # Create sale detail
                    detail_attributes = {
                        "sale": new_sale,
                        "product": product_obj,
                        "price": float(product_data["price"]),
                        "quantity": quantity_requested,
                        "total_detail": float(product_data["total_product"]),
                    }
                    SaleDetail.objects.create(**detail_attributes)
                    logger.info(f"Sale detail added: {detail_attributes}")

                messages.success(
                    request, "Sale created successfully!", extra_tags="bg-success"
                )
                return redirect("sales:sales_list")

        except ValueError as ve:
            logger.error(f"Stock error: {ve}")
            messages.error(request, str(ve), extra_tags="danger")
        except Exception as e:
            logger.error(f"Error during sale creation: {e}")
            messages.error(
                request,
                f"There was an error during the creation! Error: {e}",
                extra_tags="danger",
            )

        return redirect("sales:sales_list")

    return render(request, "inventory/sales/sales_add.html", context=context)


# =================================== Sale details view ===================================
@login_required
@admin_or_manager_or_staff_required
def sales_details_view(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)

    # Get the sale details related to the sale
    details = SaleDetail.objects.filter(sale=sale)

    context = {
        "active_icon": "sales",
        "sale": sale,
        "details": details,
    }

    return render(request, "inventory/sales/sales_details.html", context=context)


# =================================== Sale delete view ===================================
@login_required
@admin_required
@transaction.atomic
def sale_delete_view(request, sale_id):
    try:
        # Get the sale to delete
        sale = Sale.objects.get(id=sale_id)
        sale.delete()
        messages.success(
            request, f"Sale: {sale_id} deleted successfully!", extra_tags="bg-success"
        )
    except Sale.DoesNotExist:
        # Specific exception for when the sale is not found
        messages.error(
            request,
            f"Sale: {sale_id} not found!",
            extra_tags="bg-danger",
        )
    except Exception as e:
        # General exception for any other errors
        messages.error(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        print(e)
    finally:
        return redirect("sales:sales_list")


# =================================== Sale receipt view ===================================
@login_required
@admin_or_manager_or_staff_required
def receipt_pdf_view(request, sale_id):
    # Get the sale
    sale = Sale.objects.get(id=sale_id)

    # Get the sale details
    details = SaleDetail.objects.filter(sale=sale)

    # Render the template
    template = get_template("inventory/sales/sales_receipt_pdf.html")
    context = {"sale": sale, "details": details}
    html_template = template.render(context)

    # Create a file-like buffer to receive PDF data
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="receipt.pdf"'

    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(html_template, dest=response)

    # Check if PDF was created successfully
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response


# =================================== Sale Report view ===================================


@login_required
@admin_or_manager_or_staff_required
def sales_report_view(request):
    # Initialize the form with GET parameters
    form = ReportPeriodForm(request.GET or None)

    # Validate form and extract start and end dates
    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
    else:
        start_date = end_date = None

    # Fetch all sales with optional date filtering
    sales = (
        Sale.objects.all()
        .select_related("customer")
        .prefetch_related("items__product__inventory")
        .order_by("id")
    )

    # Apply date filters if provided
    if start_date:
        sales = sales.filter(trans_date__gte=start_date)
    if end_date:
        sales = sales.filter(trans_date__lte=end_date)

    # Calculate grand total for all sales
    grand_total = sales.aggregate(Sum("grand_total"))["grand_total__sum"] or 0

    # Calculate total items sold across all sales
    total_items = sum(sale.sum_items() for sale in sales)

    # Initialize totals for profit and stock balance
    total_profit = 0
    sales_with_details = []

    # Iterate over each sale to calculate profit and stock balance
    for sale in sales:
        sale_profit = sum(item.calculate_profit() for item in sale.items.all())

        # Attach the calculated profit and stock balance to the sale instance
        sale.profit = sale_profit

        # Add to overall totals
        total_profit += sale_profit

        # Add the sale to the list with details
        sales_with_details.append(sale)

    # Context to pass to the template
    context = {
        "table_title": "Sales Report",  # Title for the table
        "sales": sales_with_details,  # List of sales with detailed info
        "grand_total": grand_total,  # Total grand total for all sales
        "total_items": total_items,  # Total number of items sold across all sales
        "total_profit": total_profit,  # Total profit from all sales
        "start_date": start_date,
        "end_date": end_date,
        "form": form,
    }

    return render(request, "inventory/sales/sales_report.html", context=context)
