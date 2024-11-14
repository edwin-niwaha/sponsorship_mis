from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.inventory.sales.models import SaleDetail

# Import custom decorators
from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

from .forms import (
    CategoryForm,
    InventoryForm,
    ProductForm,
    ProductImageForm,
)

# Import models and forms
from .models import Category, Inventory, Product, ProductImage


# =================================== categories view ===================================
@login_required
@admin_or_manager_or_staff_required
def categories_list_view(request):
    context = {
        "active_icon": "products_categories",
        "categories": Category.objects.all(),
    }
    return render(request, "inventory/products/categories.html", context=context)


# =================================== categories add view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def categories_add_view(request):
    context = {
        "active_icon": "products_categories",
    }

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            # Check if a category with the same name already exists
            category_name = form.cleaned_data["name"]
            if Category.objects.filter(name=category_name).exists():
                messages.error(
                    request,
                    f"A category with the name '{category_name}' already exists.",
                    extra_tags="warning",
                )
            else:
                try:
                    # Save the form data
                    form.save()
                    messages.success(
                        request,
                        f"Category: {category_name} created successfully!",
                        extra_tags="bg-success",
                    )
                    return redirect("products:categories_list")
                except Exception as e:
                    messages.error(
                        request,
                        "There was an error during the creation!",
                        extra_tags="bg-danger",
                    )
                    print(e)
                    return redirect("products:categories_add")
        else:
            messages.error(
                request,
                "Please correct the errors below.",
                extra_tags="warning",
            )
    else:
        form = CategoryForm()

    context["form"] = form
    return render(request, "inventory/products/categories_add.html", context=context)


# =================================== categories update view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def categories_update_view(request, category_id):
    # Get the category or return a 404 error if not found
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            try:
                # Save the form data
                form.save()
                messages.success(
                    request,
                    f"Category: {form.cleaned_data['name']} updated successfully!",
                    extra_tags="bg-success",
                )
                return redirect("products:categories_list")
            except Exception as e:
                messages.error(
                    request,
                    "There was an error during the update!",
                    extra_tags="bg-danger",
                )
                print(e)
                return redirect("products:categories_list")
        else:
            messages.error(
                request,
                "Please correct the errors below.",
                extra_tags="warning",
            )
    else:
        form = CategoryForm(instance=category)

    context = {
        "active_icon": "products_categories",
        "form": form,
        "category": category,
    }

    return render(request, "inventory/products/categories_update.html", context=context)


# =================================== categories delete view ===================================
@login_required
@admin_required
@transaction.atomic
def categories_delete_view(request, category_id):
    try:
        # Get the category to delete
        category = Category.objects.get(id=category_id)
        category.delete()
        messages.success(
            request,
            "¡Category: " + category.name + " deleted!",
            extra_tags="bg-success",
        )
        return redirect("products:categories_list")
    except Exception as e:
        messages.success(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        print(e)
        return redirect("products:categories_list")


# =================================== products_list_view ===================================
@login_required
@admin_or_manager_or_staff_required
def products_list_view(request):
    # Fetch all products
    products = Product.objects.all()

    # Calculate total price and total cost without using inventory quantity
    total_price = products.aggregate(total_price=Sum("price"))["total_price"] or 0
    total_cost = products.aggregate(total_cost=Sum("cost"))["total_cost"] or 0
    total_stock = (
        products.aggregate(total_stock=Sum("inventory__quantity"))["total_stock"] or 0
    )

    context = {
        "products": products,
        "total_price": total_price,
        "total_cost": total_cost,
        "total_stock": total_stock,
        "table_title": "Products",
    }

    return render(request, "inventory/products/products.html", context=context)


# =================================== products add view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def products_add_view(request):
    context = {
        "product_status": Product.status.field.choices,
        "table_title": "Add Product",
    }

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            # Check if a product with the same attributes exists
            attributes = form.cleaned_data
            if Product.objects.filter(**attributes).exists():
                messages.error(
                    request, "Product already exists!", extra_tags="bg-warning"
                )
                return redirect("products:products_add")

            try:
                form.save()
                messages.success(
                    request,
                    f"Product: {attributes['name']} created successfully!",
                    extra_tags="bg-success",
                )
                return redirect("products:products_list")
            except Exception as e:
                messages.error(
                    request,
                    "There was an error during the creation!",
                    extra_tags="bg-danger",
                )
                print(e)
                return redirect("products:products_add")
        else:
            messages.error(
                request,
                "There were errors in the form submission.",
                extra_tags="bg-danger",
            )
    else:
        form = ProductForm()

    context["form"] = form
    return render(request, "inventory/products/products_add.html", context=context)


# =================================== products update view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def products_update_view(request, product_id):
    # Get the product or return 404 if not found
    product = get_object_or_404(Product, id=product_id)

    context = {
        "table_title": "Update Product",
        "product_status": Product.status.field.choices,
        "product": product,
        "categories": Category.objects.all(),
    }

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            # Check if a product with the same attributes exists, excluding the current product
            attributes = form.cleaned_data
            if Product.objects.filter(**attributes).exclude(id=product_id).exists():
                messages.error(
                    request,
                    "Product with the same attributes already exists!",
                    extra_tags="warning",
                )
                return redirect("products:products_update", product_id=product_id)

            try:
                form.save()
                messages.success(
                    request,
                    f"Product: {product.name} updated successfully!",
                    extra_tags="bg-success",
                )
                return redirect("products:products_list")
            except Exception as e:
                messages.error(
                    request,
                    "There was an error during the update!",
                    extra_tags="bg-danger",
                )
                print(e)
                return redirect("products:products_update", product_id=product_id)
        else:
            messages.error(
                request,
                "There were errors in the form submission.",
                extra_tags="bg-danger",
            )
    else:
        form = ProductForm(instance=product)

    context["form"] = form
    return render(request, "inventory/products/products_update.html", context=context)


# =================================== products delete view ===================================
@login_required
@admin_required
@transaction.atomic
def products_delete_view(request, product_id):
    try:
        # Get the product to delete
        product = Product.objects.get(id=product_id)
        product.delete()
        messages.success(
            request, "¡Product: " + product.name + " deleted!", extra_tags="bg-success"
        )
        return redirect("products:products_list")
    except Exception as e:
        messages.success(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        print(e)
        return redirect("products:products_list")


def product_detail_view(request, id):
    product = get_object_or_404(Product, id=id)
    images = product.images.all()  # Fetch related product images
    return render(
        request,
        "inventory/products/product_detail.html",
        {"product": product, "images": images},
    )


# =================================== Stock alerts view ===================================
@login_required
@admin_or_manager_or_staff_required
def stock_alerts_view(request):
    # Fetch products with low stock but not out of stock
    low_stock_products = Inventory.objects.filter(
        quantity__lte=F("low_stock_threshold"), quantity__gt=0
    ).select_related("product")

    # Fetch products that are out of stock
    out_of_stock_products = Inventory.objects.filter(quantity=0).select_related(
        "product"
    )

    # Passing data to the template
    context = {
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
    }

    return render(request, "inventory/products/stock_alerts.html", context)


# =================================== Upload Product Image ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def update_product_image(request):
    if request.method == "POST":
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            product_id = request.POST.get("id")
            product_image = get_object_or_404(Product, id=product_id)

            # Save the new product image without committing
            new_picture = form.save(commit=False)
            new_picture.product = product_image
            new_picture.is_default = True  # Assuming is_current means default image
            new_picture.save()

            # Update product's profile image
            product_image.image = new_picture.image
            product_image.save()

            messages.success(
                request, "Product image updated successfully!", extra_tags="bg-success"
            )
            return redirect("products:update_product_image")
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = ProductImageForm()

    # Fetch all products
    products = Product.objects.all().order_by("id")

    return render(
        request,
        "inventory/products/product_image_add.html",
        {
            "form": form,
            "form_name": "Upload Product Image",
            "products": products,
            "table_title": "Upload Image",
        },
    )


# =================================== View Product Image ===================================
@login_required
@admin_or_manager_or_staff_required
def product_images(request):
    products = Product.objects.all().order_by("id")

    if request.method == "POST":
        product_id = request.POST.get("id")

        if product_id:
            selected_product = get_object_or_404(Product, id=product_id)
            # Fetch all images related to the product
            image_fetched = ProductImage.objects.filter(product_id=product_id)

            if not image_fetched.exists():
                messages.error(
                    request,
                    "No images found for the selected product.",
                    extra_tags="bg-warning",
                )

            return render(
                request,
                "inventory/products/product_images.html",
                {
                    "table_title": "Product Images",
                    "products": products,
                    "selected_product": selected_product,  # Pass the selected product
                    "product_image_fetched": image_fetched,  # Pass the fetched images
                },
            )
        else:
            messages.error(request, "No product selected.", extra_tags="bg-danger")

    # Handle GET request or fallback if no product is selected
    return render(
        request,
        "inventory/products/product_images.html",
        {"table_title": "Product Image", "products": products},
    )


# =================================== Delete Product Image ===================================
@login_required
@admin_required
@transaction.atomic
def delete_product_image(request, pk):
    records = ProductImage.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("products:product_images"))


@login_required
@admin_or_manager_or_staff_required
def inventory_list_view(request):
    inventories = Inventory.objects.select_related("product").all()
    context = {
        "inventories": inventories,
        "table_title": "Inventory List",
    }
    return render(request, "inventory/products/inventory_list.html", context)


# =================================== inventory_report view ===================================


@login_required
@admin_or_manager_or_staff_required
def inventory_report_view(request):
    # Fetch all inventories with related products
    inventories = Inventory.objects.select_related("product").all()

    # Calculate total stock from inventory quantities
    total_stock = inventories.aggregate(total_stock=Sum("quantity"))["total_stock"] or 0

    # Prepare context for rendering
    context = {
        "active_icon": "inventory",
        "inventories": inventories,  # Ensure this matches what the template expects
        "total_stock": total_stock,
        "table_title": "Inventory Report",
    }

    return render(request, "inventory/products/inventory_report.html", context=context)


# =================================== inventory_add view ===================================


@login_required
@admin_or_manager_or_staff_required
def inventory_add_view(request):
    context = {
        "table_title": "Add Inventory",
    }

    # Initialize the form based on the request method
    if request.method == "POST":
        form = InventoryForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data[
                "product"
            ]  # Ensure 'product' field is in your form

            if Inventory.objects.filter(product=product).exists():
                messages.warning(
                    request,
                    "Oops! This product already has inventory; you can only update.",
                    extra_tags="bg-warning",
                )
            else:
                form.save()
                messages.success(
                    request, "Inventory added successfully!", extra_tags="bg-success"
                )
                return redirect(
                    "products:inventory_list"
                )  # Adjust the redirect as necessary
        else:
            messages.error(
                request,
                "There was an error in your form. Please check your input.",
                extra_tags="bg-danger",
            )
    else:
        form = InventoryForm()

    # Add the form to context, regardless of the request method or form validity
    context["form"] = form

    return render(request, "inventory/products/inventory_add.html", context=context)


# =================================== inventory_update view ===================================


@login_required
@admin_or_manager_or_staff_required
def inventory_update_view(request, pk):
    context = {
        "table_title": "Update Inventory",
    }
    # Fetch the Inventory object using pk
    inventory = get_object_or_404(Inventory, pk=pk)

    if request.method == "POST":
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Inventory updated successfully!", extra_tags="bg-success"
            )
            return redirect("products:inventory_list")
    else:
        form = InventoryForm(instance=inventory)

    context["form"] = form
    return render(request, "inventory/products/inventory_update.html", context=context)


# =================================== inventory_delete view ===================================
@login_required
@admin_required
def inventory_delete_view(request, pk):
    inventory = get_object_or_404(Inventory, id=pk)
    inventory.delete()
    messages.info(request, "Inventory deleted successfully!", extra_tags="bg-warning")
    return HttpResponseRedirect(reverse("products:inventory_list"))


# =================================== inventory_profitability_report view ===================================
@login_required
@admin_required
def product_sales_report(request):
    # Retrieve all products and their sales data
    products = Product.objects.all()

    report_data = []
    total_quantity_sold = 0
    total_revenue = 0
    total_cost = 0
    total_profit = 0
    total_quantity_in_stock = 0

    for product in products:
        # Total quantity sold for the product
        product_quantity_sold = (
            SaleDetail.objects.filter(product=product).aggregate(Sum("quantity"))[
                "quantity__sum"
            ]
            or 0
        )

        # Total revenue generated by the product (price * quantity sold)
        product_total_revenue = (
            SaleDetail.objects.filter(product=product).aggregate(Sum("total_detail"))[
                "total_detail__sum"
            ]
            or 0
        )

        # Quantity in stock (from the Inventory model)
        quantity_in_stock = (
            product.inventory.quantity if hasattr(product, "inventory") else 0
        )

        # Cost price of the product
        cost_price = Decimal(product.cost)  # Convert cost_price to Decimal
        selling_price = product.price

        # Calculate the total cost of products sold (cost * quantity sold)
        product_total_cost = cost_price * Decimal(
            product_quantity_sold
        )  # Ensure product_quantity_sold is Decimal as well

        # Calculate profit (revenue - cost)
        product_profit = (
            Decimal(product_total_revenue) - product_total_cost
        )  # Ensure product_total_revenue is Decimal

        # Add the product data to the report
        report_data.append(
            {
                "product": product,
                "total_quantity_sold": product_quantity_sold,
                "total_revenue": product_total_revenue,
                "quantity_in_stock": quantity_in_stock,
                "cost_price": cost_price,
                "selling_price": selling_price,
                "profit": product_profit,  # Calculated profit
                "profit_margin": product.profit_margin(),  # Profit margin for the product
            }
        )

        # Accumulate totals
        total_quantity_sold += product_quantity_sold
        total_revenue += product_total_revenue
        total_cost += product_total_cost
        total_profit += product_profit
        total_quantity_in_stock += quantity_in_stock

    # Set a title for the report
    table_title = "Product Sales Report"

    # Pass data to template
    return render(
        request,
        "inventory/products/product_sales_report.html",
        {
            "report_data": report_data,
            "table_title": table_title,
            "total_quantity_sold": total_quantity_sold,
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "total_quantity_in_stock": total_quantity_in_stock,
        },
    )
