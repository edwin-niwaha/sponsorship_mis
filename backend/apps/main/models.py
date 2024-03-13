from django.db import models
from PIL import Image

    
class ChildBioData(models.Model):
    first_name = models.CharField(max_length=100, blank=False)
    last_name = models.CharField(max_length=100, blank=False)
    avatar = models.ImageField(upload_to='child_profiles/', blank=True)
    residence = models.CharField(max_length=100, blank=False)
    district = models.CharField(max_length=100, blank=False)
    c_tribe = models.CharField(max_length=100, blank=False)
    gender = models.CharField(choices=(('M','Male'),('F','Female')), max_length=20)
    date_of_birth = models.DateField(null=True)

    name_of_the_school = models.CharField(max_length=100, blank=False)
    EDUC_CHOICES = (("P", "PreSchool"), ("K", "Kindergarten"), ("P", "Pimary"), ("S", "Secondary"), ("T", "Tertially"), ("U", "University"))
    education_level = models.CharField(max_length=10, choices=EDUC_CHOICES, default="P")
    CLASS_CHOICES = (
        ('Baby', 'Baby'),
        ('Middle', 'Middle'),
        ('Top', 'Top'),
        ('P1', 'Primary One'),
		('P2', 'Primary Two'),
		('P3', 'Primary Three'),
		('P4', 'Primary Four'),
		('P5', 'Primary Five'),
		('P6', 'Primary Six'),
		('P7', 'Primary Seven'),
		('F1', 'Form One'),
		('F2', 'Form Two'),
		('F3', 'Form Three'),
		('F4', 'Form Four'),
		('F5', 'Form Five'),
		('F6', 'Form Six'),
		('Ter', 'Tertially'),
		('Uni', 'University'),
    )
    child_class = models.CharField(max_length=20, choices=CLASS_CHOICES, default='Baby')
    best_subject = models.CharField(max_length=100, blank=False)
    
    c_weight = models.CharField(max_length=100, blank=False)
    c_height = models.CharField(max_length=100, blank=False)
    siblings = models.TextField(max_length=100, blank=False)
    responsibility = models.TextField(max_length=100, blank=False)
    prayer_request = models.CharField(max_length=100, blank=False)
    guardian = models.CharField(max_length=100, blank=True)
    gurdian_tel = models.CharField(max_length=100, default="+256")
    relationship_with_guardian = models.CharField(max_length=100, blank=True)
    aspiration = models.CharField(max_length=100, blank=True)
    c_intrest = models.CharField(max_length=100, blank=True)

    background_info = models.CharField(max_length=100, blank=False)
    health_status = models.CharField(max_length=100, blank=False)
    religion = models.CharField(max_length=100, blank=False)
    relationsip_with_christ = models.CharField(max_length=100, blank=False)
    is_sponsored = models.BooleanField(default=False)
    sponsorship_type = models.CharField(choices=(('F','Full Sponsorship'),('Co','Co-Sponsorship')),max_length=20)
    is_departed = models.BooleanField(default=False)
    year_enrolled = models.PositiveIntegerField(default=2000)

    father_name = models.CharField(max_length=100, blank=False)
    is_father_alive = models.BooleanField(default=False)
    father_death_year = models.CharField(max_length=100, blank=True)
    father_death_cause = models.CharField(max_length=100, blank=True)
    father_description = models.TextField(max_length=100,blank=True)
    mother_name = models.CharField(max_length=100)
    is_mother_alive = models.BooleanField(default=False)
    mother_death_year = models.CharField(max_length=100, blank=True)
    mother_death_cause = models.CharField(max_length=100, blank=True)
    mother_description = models.TextField(max_length=100, blank=True)
    staff_comment = models.TextField(max_length=100, blank=True)
    compiled_by = models.CharField(max_length=100, blank=True)

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
        return f"P-{self.pk}"
	
