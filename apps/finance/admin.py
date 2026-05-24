from django.contrib import admin

from .models import (
    ChildPayments,
    DonorPayment,
    Payment,
    StaffPayments,
    SupportProgram,
)


@admin.register(SupportProgram)
class SupportProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    date_hierarchy = "payment_date"
    list_display = (
        "sponsor",
        "program",
        "amount",
        "payment_date",
        "child",
        "staff",
        "source_model",
        "source_id",
    )
    list_filter = ("program", "payment_date")
    list_select_related = ("sponsor", "program", "child", "staff")
    search_fields = (
        "sponsor__first_name",
        "sponsor__last_name",
        "sponsor__email",
        "reference",
        "source_model",
    )
    raw_id_fields = ("sponsor", "child", "staff")
    readonly_fields = ("source_model", "source_id", "created_at")


admin.site.register(ChildPayments)
admin.site.register(DonorPayment)
admin.site.register(StaffPayments)
