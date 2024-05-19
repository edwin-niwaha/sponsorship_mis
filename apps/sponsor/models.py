import datetime
from datetime import date
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)

# =================================== SPONSOR MODEL ===================================
class Sponsor(models.Model):
    DEPARTURE_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No'),
    )
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    SPONSORSHIP_TYPE_CHOICES = (
        ('Child full support', 'Child full support'),
        ('Child co-support', 'Child co-support'),
        ('Family full support', 'Family full support'),
        ('Family co-support', 'Family co-support'),
        ('General support', 'General support'),
    )
    first_name = models.CharField(max_length=25, null=True, verbose_name="First Name")
    last_name = models.CharField(max_length=25, null=True, verbose_name="Last Name")
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, blank=False,
                               verbose_name="Gender")
    email = models.EmailField(verbose_name="Email")
    sponsorship_type_at_signup = models.CharField(
        max_length=20, choices=SPONSORSHIP_TYPE_CHOICES, null=True, blank=True, 
        verbose_name="Type of Sponsorship Interest")
    job_title = models.CharField(max_length=30, null=True, verbose_name="Job Title")
    region = models.CharField(max_length=30, null=True, verbose_name="Region")
    town = models.CharField(max_length=30, null=True, verbose_name="Town")
    origin = models.CharField(max_length=30, null=True, verbose_name="Origin")
    business_telephone = PhoneNumberField(null=True, blank=True, default="+256999999999",
                                           verbose_name="Business Telephone")
    mobile_telephone = PhoneNumberField(null=True, blank=True, default="+256999999999",
                                         verbose_name="Mobile Telephone")
    city = models.CharField(max_length=30, null=True, verbose_name="City")
    start_date = models.DateField(null=True, blank=True,
                                  verbose_name="Start Date",
                                  validators=[
                                      MinValueValidator(limit_value=datetime.date(year=2013, month=1, day=1)),
                                      MaxValueValidator(limit_value=datetime.date.today())
                                  ])
    first_street_address = models.CharField(max_length=100, null=True, verbose_name="First Street Address")
    second_street_address = models.CharField(max_length=100, null=True, verbose_name="Second Street Address")
    zip_code = models.CharField(max_length=10, null=True, verbose_name="ZIP Code")
    is_departed = models.CharField(
        max_length=3, choices=DEPARTURE_CHOICES, default='No')
    comment = models.CharField(max_length=50, null=True, verbose_name="Comment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'sponsor_details'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def prefixed_id(self):
        return f"PS-0{self.pk}"

# # =================================== SPONSORSHIP MODEL ===================================
# class Sponsorship(models.Model):
#     sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE, related_name='sponsorships')
#     child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='sponsored_by')
    
    # SPONSORSHIP_TYPE_CHOICES = (
    #     ('Full', 'Full Sponsorship'),
    #     ('Co', 'Co-Sponsorship'),
    # )
    # sponsorship_type = models.CharField(
    #     max_length=20, choices=SPONSORSHIP_TYPE_CHOICES, null=True, blank=True, verbose_name="Type of sponsorship")

#     start_date = models.DateField()
#     end_date = models.DateField(blank=True, null=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'sponsorship_details'
#         unique_together = (('child', 'sponsor'),)

#     def __str__(self):
#         return f"{self.child} sponsored by {self.sponsor}"
