from django.contrib import admin

from .models import Donor, Sponsor, SponsorDeparture, SponsorFeedback


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "is_child_sponsor",
        "is_staff_sponsor",
        "is_family_supporter",
        "is_general_donor",
        "is_one_time_donor",
        "is_departed",
    )
    list_filter = (
        "is_child_sponsor",
        "is_staff_sponsor",
        "is_family_supporter",
        "is_general_donor",
        "is_one_time_donor",
        "is_departed",
    )
    search_fields = ("first_name", "last_name", "email")


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "created_at")
    search_fields = ("full_name", "email", "phone")


@admin.register(SponsorDeparture)
class SponsorDepartureAdmin(admin.ModelAdmin):
    list_display = ("sponsor", "departure_date", "created_at")
    list_select_related = ("sponsor",)
    search_fields = ("sponsor__first_name", "sponsor__last_name", "departure_reason")


@admin.register(SponsorFeedback)
class SponsorFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "sponsor",
        "subject",
        "status",
        "email_sent_at",
        "created_at",
    )
    list_filter = ("status", "email_sent_at", "created_at")
    list_select_related = ("sponsor", "submitted_by")
    search_fields = (
        "sponsor__first_name",
        "sponsor__last_name",
        "sponsor__email",
        "subject",
        "message",
    )
    readonly_fields = ("email_sent_at", "email_error", "created_at", "updated_at")
