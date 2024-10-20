from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from apps.inventory.supplier.models import Supplier

# Define choices for product status
STATUS_CHOICES = [
    ("", "-- Choose status --"),
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
]


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Name",
    )
    description = models.CharField(
        max_length=50, blank=True, verbose_name="Description"
    )

    class Meta:
        db_table = "category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=256, verbose_name="Product Name")
    description = models.TextField(verbose_name="Product Description")
    status = models.CharField(
        choices=STATUS_CHOICES, max_length=10, verbose_name="Status"
    )
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Category",
    )
    supplier = models.ForeignKey(
        Supplier,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Supplier",
    )
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Cost Price"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Selling Price"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "product"

    def __str__(self):
        return self.name

    def to_json(self):
        item = model_to_dict(self)
        item.update(
            {
                "id": self.id,
                "text": self.name,
                "category": self.category.name if self.category else None,
                "quantity": (
                    self.inventory.quantity if hasattr(self, "inventory") else 0
                ),
                "total_product": 0,
            }
        )
        return item

    def profit_margin(self):
        """Calculate and return the profit margin as a percentage."""
        if self.price and self.cost:
            return round(((self.price - self.cost) / self.price) * 100, 2)
        return 0  # return 0 if there's no valid price or cost

    @property
    def prefixed_id(self):
        return f"SKU{self.pk:03d}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="product_images/", verbose_name="Product Image")
    is_default = models.BooleanField(default=False, verbose_name="Is Default")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "product_image"
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Image for {self.product.name} (Default: {self.is_default})"

    def clean(self):
        # Ensure only one default image is set per product
        if self.is_default:
            default_image_exists = (
                ProductImage.objects.filter(product=self.product, is_default=True)
                .exclude(id=self.id)
                .exists()
            )

            if default_image_exists:
                raise ValidationError("Only one default image can be set per product.")

    def save(self, *args, **kwargs):
        # Ensure no other images are marked as default if this one is set as default
        if self.is_default:
            ProductImage.objects.filter(product=self.product, is_default=True).update(
                is_default=False
            )

        super().save(*args, **kwargs)


class Inventory(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(verbose_name="Stock Quantity", default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=5, verbose_name="Low Stock Threshold"
    )
    is_out_of_stock = models.BooleanField(default=False, verbose_name="Out of Stock")

    def check_stock_alerts(self):
        """Check stock levels and update stock status."""
        self.is_out_of_stock = self.quantity <= 0

        # Trigger low stock alert if quantity is less than or equal to threshold
        if self.quantity <= self.low_stock_threshold and not self.is_out_of_stock:
            self.send_low_stock_alert()

    def send_low_stock_alert(self):
        """Send an alert for low stock."""
        # Implement notification logic here
        # For example, sending an email or logging the alert
        print(
            f"Low stock alert for {self.product.name}. Current stock: {self.quantity}"
        )

    def save(self, *args, **kwargs):
        # Ensure stock alerts are checked before saving
        self.check_stock_alerts()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - Stock: {self.quantity}"
