import datetime
from datetime import date
from django.core.validators import (
    FileExtensionValidator,
    RegexValidator,
    MinValueValidator,
    MaxValueValidator,
    EmailValidator,
)
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from cloudinary.models import CloudinaryField


# Clients registration
class Client(models.Model):
    # Basic info
    reg_number = models.CharField(
        max_length=10,
        verbose_name="Registration ID",
        null=True,
        blank=True,
        default="G01-001",
    )
    full_name = models.CharField(
        max_length=50,
        verbose_name="Full Name",
        validators=[
            RegexValidator(
                r"^[A-Za-z]+(?:\s[A-Za-z]+)*$", "Only letters and spaces are allowed"
            )
        ],
    )
    picture = CloudinaryField(
        "client_uploads",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
        null=True,
        blank=True,
    )
    mobile_telephone = PhoneNumberField(
        verbose_name="Mobile Telephone", null=True, blank=True, default="+256999999999"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_info"
        verbose_name = "Client Bio Data"
        verbose_name_plural = "Clients Bio Data"

    def __str__(self):
        return self.full_name


# 7Hills registration
class SevenHillsRegistration(models.Model):
    registration_date = models.DateField()
    full_name = models.CharField(max_length=255)
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date of Birth",
        validators=[
            MinValueValidator(limit_value=datetime.date(year=1900, month=1, day=1)),
            MaxValueValidator(limit_value=datetime.date.today()),
        ],
    )

    AGE_BRACKET_CHOICES = [
        ("0-17", "0 – 17"),
        ("18-25", "18 – 25"),
        ("26-34", "26 – 34"),
        ("35-45", "35 – 45"),
        ("46+", "46 and above"),
    ]
    age_bracket = models.CharField(max_length=10, choices=AGE_BRACKET_CHOICES)

    MARITAL_STATUS_CHOICES = [
        ("Single", "Single"),
        ("Married", "Married"),
        ("Widowed", "Widowed"),
        ("Divorced", "Divorced"),
        ("Domestic Partnership", "In a Domestic Partnership"),
    ]
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS_CHOICES)
    spouse_name = models.CharField(max_length=255, blank=True, null=True)
    spouse_contact = PhoneNumberField(blank=True, null=True)

    number_of_children = models.PositiveIntegerField(blank=True, null=True)
    boys = models.PositiveIntegerField(blank=True, null=True)
    girls = models.PositiveIntegerField(blank=True, null=True)

    CHILDREN_AGE_BRACKETS = [
        ("0-5", "0-5 years"),
        ("6-10", "6-10 years"),
        ("11-15", "11-15 years"),
        ("16-18", "16-18 years"),
    ]
    children_age_brackets = models.CharField(max_length=20, blank=True, null=True)

    highest_education = models.CharField(max_length=255)
    home_village = models.CharField(max_length=255)
    residence = models.CharField(max_length=255)
    email = models.EmailField(validators=[EmailValidator()])
    telephone_1 = PhoneNumberField()
    telephone_2 = PhoneNumberField(blank=True, null=True)

    next_of_kin = models.CharField(max_length=255)
    next_of_kin_telephone_1 = PhoneNumberField()
    next_of_kin_telephone_2 = PhoneNumberField(blank=True, null=True)
    relationship_with_next_of_kin = models.CharField(max_length=255)

    workplace = models.CharField(max_length=255, blank=True, null=True)

    SAVINGS_FREQUENCY_CHOICES = [
        ("Daily", "Daily"),
        ("Weekly", "Weekly"),
        ("Monthly", "Monthly"),
    ]
    savings_frequency = models.CharField(
        max_length=10, choices=SAVINGS_FREQUENCY_CHOICES, blank=True, null=True
    )
    min_savings_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    saving_goal = models.TextField(blank=True, null=True)

    SERVICES_INTERESTED = [
        ("Savings Scheme", "Join Savings Scheme"),
        ("Skills Training", "Skills Training"),
        ("Share Group", "Join Share Group"),
        ("Community Unit", "Join Community Unit"),
        ("Discipleship", "Discipleship"),
        ("Volunteering", "Volunteering"),
    ]
    services_interested = models.CharField(
        max_length=50, choices=SERVICES_INTERESTED, blank=True, null=True
    )

    MINISTRY_GROUPS = [
        ("Ushering", "Ushering"),
        ("Evangelism", "Evangelism"),
        ("Children Ministry", "Children's Ministry"),
        ("Youth Ministry", "Youth Ministry"),
        ("Intercession", "Intercession"),
        ("Choir", "Choir"),
        ("Hospitality", "Hospitality"),
        ("Media", "Media"),
    ]
    ministry_groups = models.CharField(
        max_length=50, choices=MINISTRY_GROUPS, blank=True, null=True
    )

    dc_makerere_association_year = models.PositiveIntegerField(
        blank=True, null=True, validators=[MinValueValidator(1900)]
    )
    recommended_by = models.CharField(max_length=255, blank=True, null=True)
    preferred_contact_method = models.CharField(max_length=255, blank=True, null=True)
    additional_comments = models.TextField(blank=True, null=True)
    agrees_to_photo_use = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name}"

    @property
    def prefixed_id(self):
        if self.pk < 10:
            return f"7H00{self.pk}"
        elif self.pk < 100:
            return f"7H0{self.pk}"
        else:
            return f"7H{self.pk}"

    def calculate_age(self):
        today = date.today()
        age = (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )
        return age
