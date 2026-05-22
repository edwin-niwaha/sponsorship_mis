from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "account_type",
        "staff_role",
        "role",
        "client",
        "sponsor",
    )
    list_filter = ("account_type", "staff_role", "role")
    search_fields = (
        "user__username",
        "user__email",
        "client__full_name",
        "client__reg_number",
        "client__email",
        "sponsor__first_name",
        "sponsor__last_name",
        "sponsor__email",
    )
    autocomplete_fields = ("client",)
    raw_id_fields = ("sponsor",)
