# Third-party Imports
from django.db import models
import uuid
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.auth.models import User
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
class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('card', 'Card'),
        ('mobilemoney', 'Mobile Money'),
        ('ussd', 'USSD'),
        ('banktransfer', 'Bank Transfer'),
    )

    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique internal transaction ID"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Associated user, if authenticated"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Payment amount in the specified currency"
    )
    currency = models.CharField(
        max_length=3,
        default='UGX',
        validators=[
            RegexValidator(
                regex='^(UGX|NGN|USD|KES|GHS|ZAR)$',
                message="Currency must be one of: UGX, NGN, USD, KES, GHS, ZAR"
            )
        ],
        help_text="Currency code (e.g., UGX, USD)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the payment"
    )
    customer_name = models.CharField(
        max_length=200,
        validators=[
            RegexValidator(
                regex=r'^[\w\s\-\.]+$',
                message="Name can only contain letters, numbers, spaces, hyphens, and periods"
            )
        ],
        help_text="Customer's full name"
    )
    customer_email = models.EmailField(
        help_text="Customer's email address"
    )
    transaction_ref = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique Flutterwave transaction reference"
    )
    flutterwave_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Flutterwave's transaction ID"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="Payment method used"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        help_text="Timestamp when payment was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of last update"
    )
    meta = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional metadata from Flutterwave"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_ref']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['transaction_ref'], name='unique_transaction_ref')
        ]

    def __str__(self):
        return f"{self.customer_name} - {self.amount} {self.currency} ({self.status}) - {self.transaction_ref}"

    def masked_email(self):
        """Return a partially masked email for display purposes."""
        if not self.customer_email:
            return ""
        local, domain = self.customer_email.split('@')
        masked_local = local[:2] + '****' + local[-2:] if len(local) > 4 else local
        return f"{masked_local}@{domain}"
