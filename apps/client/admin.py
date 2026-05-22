from django.contrib import admin

from .models import Client, SevenHillsRegistration


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "reg_number", "email", "mobile_telephone")
    search_fields = ("full_name", "reg_number", "email", "mobile_telephone")


@admin.register(SevenHillsRegistration)
class SevenHillsRegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "registration_date", "telephone_1", "email")
    list_filter = ("registration_date", "gender", "marital_status")
    search_fields = ("full_name", "telephone_1", "email")
