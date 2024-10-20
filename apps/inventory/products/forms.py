from django import forms
from django.core.exceptions import ValidationError
from .models import Category, Product, ProductImage, Inventory


# =================================== category form ===================================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter category name"}
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter category description",
                }
            ),
        }
        labels = {
            "name": "Category Name",
            "description": "Description",
        }


# =================================== Inventory form ===================================
class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["quantity", "low_stock_threshold"]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Enter stock quantity"}
            ),
            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter low stock threshold",
                }
            ),
        }
        labels = {
            "quantity": "Stock Quantity",
            "low_stock_threshold": "Low Stock Threshold",
        }


# =================================== product form ===================================
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "cost",
            "price",
            "description",
            "status",
            "category",
            "supplier",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter product name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter product description",
                    "rows": 3,
                }
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "supplier": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Product Name",
            "cost": "Cost Price",
            "price": "Selling Price",
            "description": "Description",
            "status": "Status",
            "category": "Category",
            "suppliers": "Suppliers",  # Label for the suppliers field
        }


# =================================== CHILD PROFILE ===================================
class ProductImageForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = ProductImage
        fields = ["image"]

        labels = {
            "image": "Upload Product Image:",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget = forms.FileInput(attrs={"accept": "image/*"})

    def clean_image(self):
        image = self.cleaned_data.get("image")
        return image


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["product", "quantity", "low_stock_threshold"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Enter stock quantity"}
            ),
            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter low stock threshold",
                }
            ),
        }
        labels = {
            "product": "Product",
            "quantity": "Stock Quantity",
            "low_stock_threshold": "Low Stock Threshold",
        }
