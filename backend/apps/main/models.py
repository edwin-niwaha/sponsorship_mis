import datetime
from django.db import models
from PIL import Image
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator, RegexValidator
from phonenumber_field.modelfields import PhoneNumberField

# for the current year 
def current_year():
    return timezone.now().year  
    
class ChildProfile(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    SPONSORSHIP_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No'),
    )
    SPONSORSHIP_TYPE_CHOICES = (
        ('Full', 'Full Sponsorship'),
        ('Co', 'Co-Sponsorship'),
    )
    EDUC_LEVEL_CHOICES = (
        ('Pre-School', 'Pre-School'),
        ('Kindergarten', 'Kindergarten'),
        ('Primary', 'Primary'),
        ('Secondary', 'Secondary'),
        ('Tertiary', 'Tertiary'),
        ('University', 'University'),
    )
    CLASS_LEVEL_CHOICES = (
        ('Baby', 'Baby'),
        ('Middle', 'Middle'),
        ('Top', 'Top'),
        ('P.1', 'Primary One'),
        ('P.2', 'Primary Two'),
        ('P.3', 'Primary Three'),
        ('P.4', 'Primary Four'),
        ('P.5', 'Primary Five'),
        ('P.6', 'Primary Six'),
        ('P.7', 'Primary Seven'),
        ('S.1', 'Form One'),
        ('S.2', 'Form Two'),
        ('S.3', 'Form Three'),
        ('S.4', 'Form Four'),
        ('S.5', 'Form Five'),
        ('S.6', 'Form Six'),
        ('Tertiary', 'Tertiary'),
        ('University', 'University'),
    )
    RELIGION_CHOICES = (
    ('Born-again Christian', 'Born-again Christian'),
    ('Anglican', 'Anglican'),
    ('Catholic', 'Catholic'),
    ('Muslim', 'Muslim'),

)
    # Basic info
    first_name = models.CharField(max_length=50, validators=[
        RegexValidator(r'^[A-Za-z]+(?:\s[A-Za-z]+)*$', 'Only letters and spaces are allowed')
    ])
    last_name = models.CharField(max_length=50, validators=[
        RegexValidator(r'^[A-Za-z]+(?:\s[A-Za-z]+)*$', 'Only letters and spaces are allowed')
    ])
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True, validators=[
    MinValueValidator(limit_value=datetime.date(year=1900, month=1, day=1)),
    MaxValueValidator(limit_value=datetime.date.today())])
    weight = models.DecimalField(max_digits=5, decimal_places=2) 
    height = models.PositiveIntegerField(validators=[MinValueValidator(1),
                                       MaxValueValidator(100)])
    avatar = models.ImageField(upload_to='child_profiles/', blank=True,
    validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    tribe = models.CharField(max_length=20)
    background_info = models.TextField(blank=True, null=True)

    # More info
    is_sponsored = models.CharField(
        max_length=3, choices=SPONSORSHIP_CHOICES, default='No')
    sponsorship_type = models.CharField(
        max_length=20, choices=SPONSORSHIP_TYPE_CHOICES, blank=True)
    relationship_with_christ = models.CharField(max_length=100, blank=False)
    health_status = models.CharField(max_length=50, blank=False)
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES, blank=False)
    residence = models.CharField(max_length=50, blank=False)
    district = models.CharField(max_length=50, blank=False)
    c_interest = models.CharField(max_length=50, blank=True)
    responsibility = models.TextField(max_length=50, blank=False)
    prayer_request = models.CharField(max_length=50, blank=False)
    aspiration = models.CharField(max_length=50, blank=True)


    # Education details
    is_child_in_school = models.CharField(
        max_length=3, choices=SPONSORSHIP_CHOICES, default='No'
    )
    name_of_the_school = models.CharField(max_length=50, blank=False)
    education_level = models.CharField(
        max_length=20, choices=EDUC_LEVEL_CHOICES, default='Pre-School'
    )
    child_class = models.CharField(
        max_length=20, choices=CLASS_LEVEL_CHOICES, blank=True
    )
    best_subject = models.CharField(max_length=50, blank=False)
    
    # Family background
    siblings = models.TextField(max_length=100, blank=True)

    # Guardian
    guardian = models.CharField(max_length=50, blank=True)
    guardian_contact_number = PhoneNumberField(blank=True, default="+256999999999")
    relationship_with_guardian = models.CharField(max_length=20, blank=True)

    # Parents
    father_name = models.CharField(max_length=100, blank=False)
    is_father_alive = models.CharField(choices=(('Yes','Yes'),('No','No')), max_length=3) 
    father_death_year = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1900)]) 
    father_death_cause = models.CharField(max_length=100, blank=True)
    father_description = models.TextField(max_length=100, blank=True)

    mother_name = models.CharField(max_length=100, blank=False)
    is_mother_alive = models.CharField(choices=(('Yes','Yes'),('No','No')), max_length=3)
    mother_death_year = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1900)])
    mother_death_cause = models.CharField(max_length=100, blank=True)
    mother_description = models.TextField(max_length=100, blank=True)

    # Other fields
    YEAR_MAX = current_year()
    year_enrolled = models.IntegerField(validators=[MinValueValidator(2013), MaxValueValidator(YEAR_MAX)])    
    
    staff_comment = models.TextField(max_length=50, blank=True)
    compiled_by = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  

    class Meta:
        db_table = 'child_info'
        verbose_name = 'Child Bio Data'
        verbose_name_plural = 'Children Bio Data'

    def __str__(self):
        return self.first_name + ' ' + self.last_name
    @property
    def prefixed_id(self):
        return f"P-00{self.pk}"
    