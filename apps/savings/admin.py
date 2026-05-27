from django.contrib import admin

from .models import SavingsAccount, SavingsTransaction


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "client", "status", "opening_date", "balance")
    list_filter = ("status", "opening_date")
    search_fields = (
        "account_number",
        "client__full_name",
        "client__reg_number",
        "client__email",
    )
    autocomplete_fields = ("client",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "transaction_type",
        "amount",
        "status",
        "transaction_date",
        "payment_method",
        "recorded_by",
        "approved_by",
    )
    list_filter = ("transaction_type", "status", "payment_method", "transaction_date")
    search_fields = (
        "account__account_number",
        "account__client__full_name",
        "account__client__reg_number",
        "reference",
    )
    readonly_fields = ("created_at", "updated_at", "approved_at")
