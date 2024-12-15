from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import F, Sum, Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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
    # Get search query from the request
    search_query = request.GET.get("search", "")

    # Filter categories based on the search query
    if search_query:
        categories = Category.objects.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
    else:
        categories = Category.objects.all()

    # If no categories are found, handle empty case
    if not categories.exists():
        context = {
            "active_icon": "products_categories",
            "categories": [],
            "search_query": search_query,
            "error_message": "No categories available for the given search criteria.",
        }
        return render(request, "inventory/products/categories.html", context)

    # Pagination setup
    paginator = Paginator(categories, 10)  # Show 10 categories per page
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.get_page(page_number)
    except:
        raise Http404("Page not found")

    context = {
        "active_icon": "products_categories",
        "categories": page_obj,
        "search_query": search_query,  # Pass search query to keep in the input
    }

    return render(request, "inventory/products/categories.html", context)


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
    # Get search query from the request
    search_query = request.GET.get("search", "")

    # Filter products based on search query
    if search_query:
        # Adjust the filter to handle ForeignKey relationships
        products = Product.objects.filter(
            Q(name__icontains=search_query)
            | Q(category__name__icontains=search_query)  # Filter by category name
            | Q(supplier__name__icontains=search_query)  # Filter by supplier name
        )
    else:
        products = Product.objects.all()

    # If no products are found, handle empty case
    if not products.exists():
        context = {
            "products": [],
            "total_price": 0,
            "total_cost": 0,
            "total_stock": 0,
            "table_title": "Products",
            "search_query": search_query,
            "error_message": "No products available for the given search criteria.",
        }
        return render(request, "inventory/products/products.html", context)

    # Pagination setup
    paginator = Paginator(products, 10)  # Show 10 products per page
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.get_page(page_number)
    except:
        # If the page number is invalid, raise 404 error
        raise Http404("Page not found")

    # Calculate totals
    total_price = products.aggregate(total_price=Sum("price"))["total_price"] or 0
    total_cost = products.aggregate(total_cost=Sum("cost"))["total_cost"] or 0
    total_stock = (
        products.aggregate(total_stock=Sum("inventory__quantity"))["total_stock"] or 0
    )

    context = {
        "products": page_obj,
        "total_price": total_price,
        "total_cost": total_cost,
        "total_stock": total_stock,
        "table_title": "Products",
        "search_query": search_query,  # Pass search query to keep in the input
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
    # Query Inventory and include related Product details
    queryset = Inventory.objects.select_related("product").all()

    # Search functionality: filter by product name if search_query is provided
    search_query = request.GET.get("search", "")  # Default to empty string if no search
    if search_query:
        queryset = queryset.filter(product__name__icontains=search_query)

    # Pagination
    paginator = Paginator(queryset, 10)  # 10 items per page
    page = request.GET.get("page")

    try:
        inventories = paginator.page(page)
    except PageNotAnInteger:
        inventories = paginator.page(1)  # First page if invalid page
    except EmptyPage:
        inventories = paginator.page(paginator.num_pages)  # Last page if out of range

    context = {
        "inventories": inventories,
        "table_title": "Inventory List",
        "search_query": search_query,  # Pass search query to the template
    }
    return render(request, "inventory/products/inventory_list.html", context)


# =================================== inventory_report view ===================================


@login_required
@admin_or_manager_or_staff_required
def inventory_report_view(request):
    # Fetch all inventories with related products
    inventories = Inventory.objects.select_related("product").all()

    # Add pagination
    paginator = Paginator(inventories, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate total stock from inventory quantities
    total_stock = inventories.aggregate(total_stock=Sum("quantity"))["total_stock"] or 0

    # Prepare context for rendering
    context = {
        "active_icon": "inventory",
        "inventories": page_obj,
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
