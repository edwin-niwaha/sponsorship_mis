import datetime
from datetime import date

from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


# =================================== CHILD MODEL ===================================
def current_year():
    return timezone.now().year


class Child(models.Model):
    # Basic info
    full_name = models.CharField(
        max_length=50,
        verbose_name="Full Name",
        validators=[
            RegexValidator(
                r"^[A-Za-z]+(?:\s[A-Za-z]+)*$", "Only letters and spaces are allowed"
            )
        ],
    )
    preferred_name = models.CharField(
        max_length=50, verbose_name="Preferred Name", null=True, blank=True
    )
    residence = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Current Residence"
    )
    district = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Home District"
    )
    tribe = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Tribe",
    )

    GENDER_CHOICES = (
        ("Male", "Male"),
        ("Female", "Female"),
    )
    gender = models.CharField(
        max_length=6, choices=GENDER_CHOICES, blank=False, verbose_name="Gender"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date of Birth",
        validators=[
            MinValueValidator(limit_value=datetime.date(year=1900, month=1, day=1)),
            MaxValueValidator(limit_value=datetime.date.today()),
        ],
    )
    picture = models.ImageField(
        default="default.jpg",
        upload_to="current_child_profiles/",
        verbose_name="Upload Image(jpg, jpeg, png)",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Weight in kilograms",
    )
    height = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(300)],
        null=True,
        blank=True,
        verbose_name="Height in centimeters",
    )

    aspiration = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Aspiration"
    )
    c_interest = models.TextField(
        max_length=100, null=True, blank=True, verbose_name="Interest and abilities "
    )

    is_child_in_school = models.BooleanField(
        default=False,
        verbose_name="Is the Child in School?",
    )

    is_sponsored = models.BooleanField(
        default=False,
        verbose_name="Is the Child sponsored?",
    )
    # Family background
    # Parents
    father_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Father’s Name"
    )
    is_father_alive = models.CharField(
        choices=(("Yes", "Yes"), ("No", "No")),
        max_length=10,
        verbose_name="Is the father alive?",
    )

    father_description = models.TextField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="if not what happened/if alive what is happening?",
    )
    mother_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Mother’s name"
    )
    is_mother_alive = models.CharField(
        choices=(("Yes", "Yes"), ("No", "No")),
        max_length=10,
        verbose_name="is the mother alive?",
    )
    mother_description = models.TextField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="if not what happened/if alive what is happening?",
    )
    # Guardian
    guardian = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Current guardian"
    )
    guardian_contact = PhoneNumberField(
        null=True, blank=True, default="+256999999999", verbose_name="Guardian Contact"
    )
    relationship_with_guardian = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Relationship with the Guardian",
    )
    # Foreign table for siblings relations
    siblings = models.TextField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="List names and age of the siblings",
    )

    background_info = models.TextField(
        blank=True, null=True, verbose_name="Other family back ground information"
    )
    health_status = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="General health status"
    )
    responsibility = models.TextField(
        max_length=50, null=True, blank=True, verbose_name="Child’s responsibilities"
    )
    relationship_with_christ = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Relationship with Christ"
    )

    RELIGION_CHOICES = (
        ("Born-again Christian", "Born-again Christian"),
        ("Anglican", "Anglican"),
        ("Catholic", "Catholic"),
        ("Muslim", "Muslim"),
    )
    religion = models.CharField(
        max_length=50,
        choices=RELIGION_CHOICES,
        null=True,
        blank=True,
        verbose_name="Religion of the Child",
    )
    prayer_request = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Prayer needs/request"
    )
    YEAR_MAX = current_year()
    year_enrolled = models.IntegerField(
        validators=[MinValueValidator(2013), MaxValueValidator(YEAR_MAX)],
        verbose_name="The year when the child was enrolled on the program?",
    )

    is_departed = models.BooleanField(
        default=False,
        verbose_name="Is the Child departed?",
    )

    # Other fields
    staff_comment = models.TextField(
        max_length=50, null=True, blank=True, verbose_name="Staff Comment "
    )
    compiled_by = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="Compiled by"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "child_info"
        verbose_name = "Child Bio Data"
        verbose_name_plural = "Children Bio Data"

    def __str__(self):
        return self.full_name

    # @property
    # def prefixed_id(self):
    #     return f"CH-00{self.pk}"

    @property
    def prefixed_id(self):
        if self.pk < 10:
            return f"CH-00{self.pk}"
        elif self.pk < 100:
            return f"CH-0{self.pk}"
        else:
            return f"CH-{self.pk}"
        

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


# =================================== CHILD PROFILE PICTURES MODEL ===================================


class ChildProfilePicture(models.Model):
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="profile_picture",
        verbose_name="Child",
    )
    picture = models.ImageField(
        default="current_child_profiles/default.jpg",
        upload_to="current_child_profiles/",
        blank=True,
        null=True,
        verbose_name="Upload Image(jpg, jpeg, png)",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
    )

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded at")
    is_current = models.BooleanField(default=False, verbose_name="Is Current Picture")

    class Meta:
        db_table = "child_pictures"
        verbose_name = "Child Profile Picture"
        verbose_name_plural = "Child Profile Pictures"
        ordering = ["-uploaded_at"]
        unique_together = ("child", "picture")

    def __str__(self):
        return (
            f"Profile picture of {self.child.full_name} uploaded at {self.uploaded_at}"
        )


# =================================== CHILD PROGRESS MODEL ===================================


class ChildProgress(models.Model):
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="progresses",
        verbose_name="Child",
    )
    name_of_school = models.CharField(max_length=50, verbose_name="Name of the School")
    previous_schools = models.TextField(
        max_length=200, verbose_name="Previous Schools Attended"
    )
    EDUC_LEVEL_CHOICES = [
        ("Pre-School", "Pre-School"),
        ("Kindergarten", "Kindergarten"),
        ("Primary", "Primary"),
        ("Secondary", "Secondary"),
        ("Tertiary", "Tertiary"),
        ("University", "University"),
    ]
    education_level = models.CharField(
        choices=EDUC_LEVEL_CHOICES,
        default="Pre-School",
        verbose_name="Level of Education",
        max_length=20,
    )
    CLASS_LEVEL_CHOICES = [
        ("", "Select Class"),
        ("Baby", "Baby"),
        ("Middle", "Middle"),
        ("Top", "Top"),
        ("P.1", "Primary One"),
        ("P.2", "Primary Two"),
        ("P.3", "Primary Three"),
        ("P.4", "Primary Four"),
        ("P.5", "Primary Five"),
        ("P.6", "Primary Six"),
        ("P.7", "Primary Seven"),
        ("S.1", "Form One"),
        ("S.2", "Form Two"),
        ("S.3", "Form Three"),
        ("S.4", "Form Four"),
        ("S.5", "Form Five"),
        ("S.6", "Form Six"),
        ("Tertiary", "Tertiary"),
        ("University", "University"),
    ]
    child_class = models.CharField(
        max_length=30,
        choices=CLASS_LEVEL_CHOICES,
        verbose_name="Class",
    )
    best_subject = models.CharField(max_length=30, verbose_name="Best Subject")
    score = models.IntegerField(
        verbose_name="Score",
        default=0,
    )
    co_curricular_activity = models.CharField(
        max_length=50,
        verbose_name="Co-curricular Activity (Optional)",
        null=True,
        blank=True,
    )
    responsibility_at_school = models.CharField(
        max_length=50,
        verbose_name="Responsibility at School (Optional)",
        null=True,
        blank=True,
    )
    future_plans = models.TextField(
        max_length=200,
        verbose_name="Future Plans",
    )
    responsibility_at_home = models.TextField(
        verbose_name="Responsibility at Home (Optional)", null=True, blank=True
    )
    notes = models.TextField(
        max_length=200, verbose_name="Notes (Optional)", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "child_progress"
        verbose_name = "Child Progress"
        verbose_name_plural = "Children Progress"

    def __str__(self):
        return f"{self.child.full_name} - {self.name_of_school}"


# =================================== CHILD CORRESPONDENCE MODEL ===================================


class ChildCorrespondence(models.Model):
    SOURCE_CHOICES = [
        ("", "Select correspondence source"),  # Default option
        ("CHILD", "Child"),
        ("SPONSOR", "Sponsor"),
    ]

    CORRESPONDENCE_CHOICES = [
        ("", "Select correspondence type"),  # Default option
        ("Christmas Gift", "Christmas Gift"),
        ("Birthday Gift", "Birthday Gift"),
        ("Letter", "Letter"),
        ("Package", "Package"),
        ("Money", "Money"),
        ("Photo", "Photo"),
    ]

    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        related_name="correspondences",
        verbose_name="Child",
    )
    correspondence_type = models.CharField(
        max_length=20,
        choices=CORRESPONDENCE_CHOICES,
        verbose_name="Select the type of correspondence",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        verbose_name="Select the source of correspondence",
    )
    attachment = models.FileField(
        upload_to="correspondence_attachments/",
        blank=True,
        null=True,
        verbose_name="Attachment",
    )
    comment = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Any comment?"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    # sponsor = models.ForeignKey(
    #     "Sponsor",
    #     on_delete=models.CASCADE,
    #     related_name="correspondences",
    #     verbose_name="Sponsor",
    # )

    class Meta:
        verbose_name = "Child Correspondence"
        verbose_name_plural = "Child Correspondences"
        db_table = "child_corres"

    def __str__(self):
        return f"{self.child} - {self.correspondence_type}"


# =================================== CHILD INCIDENT MODEL ===================================
class ChildIncident(models.Model):
    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name="incidents", verbose_name="Child"
    )
    incident_date = models.DateField(
        verbose_name="Incident Date",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(limit_value=datetime.date(year=1900, month=1, day=1)),
            MaxValueValidator(limit_value=datetime.date.today()),
        ],
    )
    description = models.TextField(
        max_length=100, verbose_name="Description of the Incident"
    )
    action_taken = models.CharField(max_length=100, verbose_name="Action Taken")
    results = models.CharField(
        max_length=100, verbose_name="Results after Action Taken"
    )
    reported_by = models.CharField(max_length=25, verbose_name="Reported By")
    followed_up_by = models.CharField(max_length=25, verbose_name="Followed Up By")
    attachment = models.FileField(
        upload_to="incident_attachments/",
        blank=True,
        null=True,
        verbose_name="Attachment",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Child Incident"
        verbose_name_plural = "Child Incidents"
        db_table = "child_incident"

    def __str__(self):
        return f"Incident of {self.child.full_name} on {self.incident_date}"


# =================================== CHILD DEPATURE MODEL ===================================
class ChildDepart(models.Model):
    child = models.ForeignKey(
        "Child",
        on_delete=models.CASCADE,
        verbose_name="Child Information",
        related_name="departures",
    )
    depart_date = models.DateField(
        verbose_name="Departure Date",
        null=True,
        blank=True,
    )
    depart_reason = models.TextField(verbose_name="Reason for Departure")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Child Departure"
        verbose_name_plural = "Child Departures"
