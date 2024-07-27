# Third-party Imports
from django.db import models

# Local App Imports
from apps.child.models import Child
from apps.sponsor.models import Sponsor
from apps.staff.models import Staff


# sponsorship_type constants
class SponsorshipType:
    CHILD_FULL_SUPPORT = "Child full support"
    CHILD_CO_SUPPORT = "Child co-support"
    FAMILY_FULL_SUPPORT = "Family full support"
    FAMILY_CO_SUPPORT = "Family co-support"
    GENERAL_SUPPORT = "General support"


SPONSORSHIP_TYPE_CHOICES = (
    ("", "--choose sponsorship type--"),
    (SponsorshipType.CHILD_FULL_SUPPORT, "Child full support"),
    (SponsorshipType.CHILD_CO_SUPPORT, "Child co-support"),
    (SponsorshipType.FAMILY_FULL_SUPPORT, "Family full support"),
    (SponsorshipType.FAMILY_CO_SUPPORT, "Family co-support"),
    (SponsorshipType.GENERAL_SUPPORT, "General support"),
)


# =================================== CHILD SPONSORSHIP MODEL ===================================
class ChildSponsorship(models.Model):
    sponsor = models.ForeignKey(
        Sponsor, on_delete=models.CASCADE, related_name="sponsored_children"
    )
    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name="sponsorships_received"
    )
    sponsorship_type = models.CharField(
        max_length=20,
        choices=SPONSORSHIP_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Sponsorship Type",
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    end_date = models.DateField(blank=True, null=True, verbose_name="End Date")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "child_sp_details"
        verbose_name_plural = "Child Sponsorships"
        unique_together = (("child", "sponsor"),)

    def __str__(self):
        return f"{self.child} sponsored by {self.sponsor}"


# =================================== STAFF SPONSORSHIP MODEL ===================================
class StaffSponsorship(models.Model):
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.CASCADE,
        verbose_name="Sponsor",
        related_name="sponsored_staff",
    )
    staff = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="sponsorships_received"
    )
    sponsorship_type = models.CharField(
        max_length=20,
        choices=SPONSORSHIP_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Sponsorship Type",
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="End Date")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "staff_sponsorship"
        verbose_name_plural = "Staff Sponsorships"
        unique_together = (("staff", "sponsor"),)

    def __str__(self):
        return f"{self.staff} sponsored by {self.sponsor}"
