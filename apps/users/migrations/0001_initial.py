# Generated by Django 4.2.15 on 2024-12-07 19:23

import apps.users.models
import cloudinary.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Contact",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Your Name")),
                ("email", models.EmailField(max_length=254, verbose_name="Your Email")),
                ("message", models.TextField(verbose_name="Message")),
                ("is_valid", models.BooleanField(default=False, verbose_name="Valid?")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
            ],
            options={
                "verbose_name": "User Feedback",
                "db_table": "user_feedback",
            },
        ),
        migrations.CreateModel(
            name="DocumentUpload",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=50, verbose_name="Document Title"),
                ),
                (
                    "file",
                    cloudinary.models.CloudinaryField(
                        max_length=255,
                        validators=[apps.users.models.validate_file_extension],
                        verbose_name="documents",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Document Upload",
                "verbose_name_plural": "Document Uploads",
                "db_table": "document_uploads",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Ebook",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("author", models.CharField(max_length=200)),
                (
                    "ebook_file",
                    cloudinary.models.CloudinaryField(
                        max_length=255, verbose_name="ebook_file"
                    ),
                ),
                ("upload_date", models.DateField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Policy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                (
                    "upload",
                    cloudinary.models.CloudinaryField(
                        blank=True, max_length=255, null=True, verbose_name="policies"
                    ),
                ),
                ("is_valid", models.BooleanField(default=False, verbose_name="Valid?")),
                ("date_reviewed", models.DateField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("administrator", "Administrator"),
                            ("manager", "Manager"),
                            ("staff", "Staff"),
                            ("guest", "Guest"),
                        ],
                        default="guest",
                        max_length=15,
                    ),
                ),
                (
                    "avatar",
                    cloudinary.models.CloudinaryField(
                        default="default.jpg", max_length=255, verbose_name="avatar"
                    ),
                ),
                ("bio", models.TextField()),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PolicyRead",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "read_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="users.policy"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "policy")},
            },
        ),
    ]
