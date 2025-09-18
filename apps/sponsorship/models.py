# Third-party Imports
import uuid
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import User
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


# =================================== PAYMENT MODEL ===================================

class Donor(models.Model):
    name = models.CharField(max_length=200, blank=False)
    phone_number = PhoneNumberField(blank=False, help_text="Format: +256xxxxxxxxx")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone_number']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['phone_number'], name='unique_donor_phone'),
        ]

    def __str__(self):
        return self.name

class Donation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1.00)],
        blank=False,
    )
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    momo_reference_id = models.UUIDField(unique=True, editable=False, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['momo_reference_id']),
            models.Index(fields=['transaction_id']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['momo_reference_id'], name='unique_momo_reference'),
            models.UniqueConstraint(fields=['transaction_id'], name='unique_transaction_id', condition=models.Q(transaction_id__isnull=False)),
        ]

    def save(self, *args, **kwargs):
        if not self.momo_reference_id:
            self.momo_reference_id = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donor.name} - {self.amount} - {self.status}"
