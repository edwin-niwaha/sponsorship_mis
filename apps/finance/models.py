# Standard Library Imports
from datetime import date
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

# Third-party Imports
from django.db import models
from django.utils.translation import gettext_lazy as _

# Local App Imports
from apps.child.models import Child
from apps.sponsor.models import Sponsor, Donor
from apps.staff.models import Staff

# =================================== CHILD-SPONSOR PAYMENT MODEL ===================================
# Define choices for months
MONTH_CHOICES = (
    ("", "--select month--"),
    ("January", "January"),
    ("February", "February"),
    ("March", "March"),
    ("April", "April"),
    ("May", "May"),
    ("June", "June"),
    ("July", "July"),
    ("August", "August"),
    ("September", "September"),
    ("October", "October"),
    ("November", "November"),
    ("December", "December"),
)


class ChildPayments(models.Model):
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.CASCADE,
        related_name="child_payments",
        verbose_name=_("Sponsor"),
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="child_payments_received",
        verbose_name=_("Child"),
        null=True,
        blank=True,
    )
    payment_date = models.DateField(
        _("Date of payment"),
        validators=[
            MinValueValidator(limit_value=date(2018, 1, 1)),
            MaxValueValidator(limit_value=date.today),
        ],
    )
    month = models.CharField(
        _("Month of payment"), max_length=20, choices=MONTH_CHOICES
    )
    payment_year = models.IntegerField(_("Year of payment"), default=2018)
    amount = models.DecimalField(
        _("Amount"), max_digits=10, decimal_places=2, default=0
    )
    # amount = models.IntegerField(_('Amount'), default=0)
    is_valid = models.BooleanField(
        default=False,
        verbose_name="Valid?",
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        db_table = "child_payments"
        verbose_name = _("Child Payment")
        verbose_name_plural = _("Child Payments")

    def __str__(self):
        return f"{self.sponsor} - {self.child} - {self.month}"

# =================================== DONOR PAYMENT MODEL ===================================

class DonorPayment(models.Model):
    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name="donor_payments",
        verbose_name=_("Donor"),
    )
    payment_date = models.DateField(
        _("Date of payment"),
        validators=[
            MinValueValidator(limit_value=date(2018, 1, 1)),
            MaxValueValidator(limit_value=date.today),  
        ],
    )
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        db_table = "donor_payments"
        verbose_name = _("Donor Payment")
        verbose_name_plural = _("Donor Payments")

    def __str__(self):
        return f"{self.donor} - {self.month} {self.payment_year}"


# =================================== STAFF-SPONSOR PAYMENT MODEL ===================================
class StaffPayments(models.Model):
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.CASCADE,
        related_name="staff_payments",
        verbose_name=_("Sponsor"),
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name="staff_payments_received",
        verbose_name=_("Staff"),
    )
    payment_date = models.DateField(
        _("Date of payment"),
        validators=[
            MinValueValidator(limit_value=date(2018, 1, 1)),
            MaxValueValidator(limit_value=date.today),
        ],
    )
    month = models.CharField(
        _("Month of payment"), max_length=20, choices=MONTH_CHOICES
    )
    payment_year = models.IntegerField(_("Year of payment"), default=2018)
    amount = models.DecimalField(
        _("Amount"), max_digits=10, decimal_places=2, default=0
    )
    is_valid = models.BooleanField(
        default=False,
        verbose_name=_("Valid?"),
    )
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        db_table = "staff_payments"
        verbose_name = _("Staff Payment")
        verbose_name_plural = _("Staff Payments")

    def __str__(self):
        return f"{self.sponsor} - {self.staff.first_name} {self.staff.last_name} - {self.month}"
