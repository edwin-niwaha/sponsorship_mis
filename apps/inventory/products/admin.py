from django.contrib import admin

# Register your models here.
from .models import Category, Inventory, Product, ProductVariant, StockMovement

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(Inventory)
admin.site.register(StockMovement)
