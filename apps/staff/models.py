import datetime

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


# =================================== STAFF MODEL ===================================
class Staff(models.Model):
    GENDER_CHOICES = (
        ("", "--choose gender--"),
        ("Male", "Male"),
        ("Female", "Female"),
    )
    DEPARTMENT_CHOICES = (
        ("", "--select department--"),
        ("ACCOUNTS", "ACCOUNTS"),
        ("PROGRAMS", "PROGRAMS"),
        ("BUSINESS OPERATIONS", "BUSINESS OPERATIONS"),
    )
    MARITAL_STATUS_CHOICES = (
        ("", "--select marital status--"),
        ("Single", "Single"),
        ("Married", "Married"),
        ("Divorced", "Divorced"),
        ("Widowed", "Widowed"),
        ("In a domestic partnership", "In a domestic partnership"),
    )

    first_name = models.CharField(max_length=25, null=True, verbose_name="First Name")
    last_name = models.CharField(max_length=25, null=True, verbose_name="Last Name")
    picture = models.ImageField(
        default="default.jpg",
        upload_to="staff_profiles/",
        verbose_name="Upload Image(jpg, jpeg, png)",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
    )
    gender = models.CharField(
        max_length=6, choices=GENDER_CHOICES, blank=False, verbose_name="Gender"
    )
    marital_status = models.CharField(max_length=30, choices=MARITAL_STATUS_CHOICES)
    email = models.EmailField(verbose_name="Email")
    home_district = models.CharField(
        max_length=30, null=True, verbose_name="Home District"
    )
    mobile_telephone = PhoneNumberField(
        null=True, blank=True, default="+256999999999", verbose_name="Mobile Telephone"
    )
    date_started_work = models.DateField(
        null=True,
        blank=True,
        verbose_name="Start Date",
        validators=[
            MinValueValidator(limit_value=datetime.date(year=2013, month=1, day=1)),
        ],
    )
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        null=True,
        blank=True,
        verbose_name="Department",
    )
    job_title = models.CharField(max_length=30, null=True, verbose_name="Job Title")
    is_departed = models.BooleanField(
        default=False,
        verbose_name="Is the Staff departed?",
    )

    is_sponsored = models.BooleanField(
        default=False,
        verbose_name="Is the Staff sponsored?",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "staff_details"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def prefixed_id(self):
        if self.pk < 10:
            return f"ST00{self.pk}"
        elif self.pk < 100:
            return f"ST0{self.pk}"
        else:
            return f"ST{self.pk}"


# =================================== STAFF DEPARTURE MODEL ===================================


class StaffDeparture(models.Model):
    staff = models.ForeignKey(
        "Staff",
        on_delete=models.CASCADE,
        verbose_name="Staff Information",
        related_name="departures",
    )
    departure_date = models.DateField(
        verbose_name="Departure Date", null=True, blank=True
    )
    departure_reason = models.TextField(verbose_name="Reason for Departure")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Staff Departure"
        verbose_name_plural = "Staff Departures"
