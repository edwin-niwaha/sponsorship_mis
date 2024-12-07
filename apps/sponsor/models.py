import datetime
from django.core.validators import MaxValueValidator, MinValueValidator

# Third-party Imports
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


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


# =================================== SPONSOR MODEL ===================================
class Sponsor(models.Model):
    DEPARTURE_CHOICES = (
        ("Yes", "Yes"),
        ("No", "No"),
    )
    GENDER_CHOICES = (
        ("Male", "Male"),
        ("Female", "Female"),
    )

    first_name = models.CharField(max_length=50, null=True, verbose_name="First Name")
    last_name = models.CharField(max_length=50, null=True, verbose_name="Last Name")
    gender = models.CharField(
        max_length=6, choices=GENDER_CHOICES, blank=False, verbose_name="Gender"
    )
    email = models.EmailField(verbose_name="Email")
    sponsorship_type = models.CharField(
        max_length=50,
        choices=SPONSORSHIP_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Sponsorship Type",
    )
    expected_amt = models.DecimalField(
        _("Amount Expected(UgX)"), max_digits=10, decimal_places=2, default=0
    )
    job_title = models.CharField(max_length=100, null=True, verbose_name="Job Title")
    region = models.CharField(max_length=100, null=True, verbose_name="Region")
    town = models.CharField(max_length=100, null=True, verbose_name="Town")
    origin = models.CharField(max_length=100, null=True, verbose_name="Origin")
    business_telephone = PhoneNumberField(
        null=True,
        blank=True,
        default="+256999999999",
        verbose_name="Business Telephone",
    )
    mobile_telephone = PhoneNumberField(
        null=True, blank=True, default="+256999999999", verbose_name="Mobile Telephone"
    )
    city = models.CharField(max_length=30, null=True, verbose_name="City")
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Start Date",
        validators=[
            MinValueValidator(limit_value=datetime.date(year=2013, month=1, day=1)),
            MaxValueValidator(limit_value=datetime.date.today()),
        ],
    )
    first_street_address = models.CharField(
        max_length=100, null=True, verbose_name="First Street Address"
    )
    second_street_address = models.CharField(
        max_length=100, null=True, verbose_name="Second Street Address"
    )
    zip_code = models.CharField(
        max_length=50, null=True, verbose_name="ZIP Code or Box Number"
    )
    is_departed = models.BooleanField(
        default=False,
        verbose_name="Departed?",
    )
    comment = models.CharField(max_length=100, null=True, verbose_name="Comment")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "sponsor_details"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def prefixed_id(self):
        if self.pk < 10:
            return f"PS00{self.pk}"
        elif self.pk < 100:
            return f"PS0{self.pk}"
        else:
            return f"PS{self.pk}"


# =================================== SPONSOR DEPARTURE MODEL ===================================


class SponsorDeparture(models.Model):
    sponsor = models.ForeignKey(
        Sponsor,  # Direct reference to the Sponsor model
        on_delete=models.CASCADE,
        verbose_name="Sponsor Information",
        related_name="departures",
    )
    departure_date = models.DateField(
        verbose_name="Departure Date", null=True, blank=True
    )
    departure_reason = models.TextField(verbose_name="Reason for Departure")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Sponsor Departure"
        verbose_name_plural = "Sponsor Departures"
