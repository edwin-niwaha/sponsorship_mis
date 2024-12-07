import os
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import requests
from io import BytesIO
from cloudinary.uploader import upload
from cloudinary.models import CloudinaryField
from django.core.files.uploadedfile import InMemoryUploadedFile

from django.db import models
from PIL import Image

# =================================== Profile Model  ===================================


class Profile(models.Model):
    ROLE_CHOICES = (
        ("administrator", "Administrator"),
        ("manager", "Manager"),
        ("staff", "Staff"),
        ("guest", "Guest"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default="guest")
    avatar = CloudinaryField("avatar", default="default.jpg")
    bio = models.TextField()

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if isinstance(self.avatar, CloudinaryField):
            # If the avatar is already a Cloudinary resource
            response = requests.get(self.avatar.url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))

                # Resize if necessary
                if img.height > 100 or img.width > 100:
                    output = BytesIO()
                    img.thumbnail((100, 100))
                    img.save(output, format=img.format)
                    output.seek(0)

                    # Re-upload resized image to Cloudinary
                    upload_result = upload(output, folder="profile_images")
                    self.avatar = upload_result["public_id"]

        elif isinstance(self.avatar, InMemoryUploadedFile):
            # If a new file is being uploaded
            img = Image.open(self.avatar)

            # Resize if necessary
            if img.height > 100 or img.width > 100:
                output = BytesIO()
                img.thumbnail((100, 100))
                img.save(output, format=img.format)
                output.seek(0)

                # Upload resized image to Cloudinary
                upload_result = upload(output, folder="profile_images")
                self.avatar = upload_result["public_id"]

        super().save(*args, **kwargs)


# =================================== Contact Model  ===================================
class Contact(models.Model):
    name = models.CharField(max_length=100, verbose_name="Your Name")
    email = models.EmailField(verbose_name="Your Email")
    message = models.TextField(verbose_name="Message")
    is_valid = models.BooleanField(default=False, verbose_name="Valid?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "User Feedback"
        db_table = "user_feedback"

    def __str__(self):
        return f"Feedback from {self.name} ({self.email})"


# =================================== Policy Model  ===================================
class Policy(models.Model):
    title = models.CharField(max_length=50)
    # upload = models.FileField(upload_to="policies/", blank=True, null=True)
    upload = CloudinaryField("policies", resource_type="auto",
                                 null=True, 
                                 blank=True)

    is_valid = models.BooleanField(
        default=False,
        verbose_name="Valid?",
    )
    date_reviewed = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# =================================== PolicyRead Model ===================================
class PolicyRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    class Meta:
        unique_together = ("user", "policy")

    def __str__(self):
        return f"{self.user.username} read {self.policy.title}"


# =================================== Ebook Model  ===================================
class Ebook(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    # ebook_file = models.FileField(upload_to="ebooks/")
    ebook_file = CloudinaryField(
        "ebook_file", resource_type="auto"
    )  # Handles all file types
    upload_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# =================================== Document Uploads  ===================================
# Custom validator function
def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = [".pdf", ".xls", ".xlsx"]
    if ext.lower() not in valid_extensions:
        raise ValidationError(
            "Unsupported file extension. Only PDF and Excel files are allowed."
        )


class DocumentUpload(models.Model):
    title = models.CharField(max_length=50, verbose_name="Document Title")
    # file = models.FileField(
    #     upload_to="default_uploads/", validators=[validate_file_extension]
    # )
    file = CloudinaryField(
        "documents",
        resource_type="auto",  # auto detects the resource type (image, pdf, etc.)
        validators=[validate_file_extension],  # Apply the file extension validator
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document Upload"
        verbose_name_plural = "Document Uploads"
        ordering = ["-created_at"]
        db_table = "document_uploads"

    def __str__(self):
        return self.title
