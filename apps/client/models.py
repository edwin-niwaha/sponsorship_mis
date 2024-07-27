from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Client(models.Model):
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
    picture = models.ImageField(
        default="default.jpg",
        upload_to="client_uploads/",
        verbose_name="Upload Image(jpg, jpeg, png)",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
    )
    reg_number = models.CharField(
        max_length=10,
        verbose_name="Registration ID",
        null=True,
        blank=True,
        default="G01-001",
    )
    mobile_telephone = PhoneNumberField(
        verbose_name="Mobile Telephone", null=True, blank=True, default="+256999999999"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_info"
        verbose_name = "Client Bio Data"
        verbose_name_plural = "Clients Bio Data"

    def __str__(self):
        return self.full_name
