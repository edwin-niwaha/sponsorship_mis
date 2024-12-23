# Generated by Django 4.2.15 on 2024-12-07 19:23

import cloudinary.models
import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Staff",
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
                    "first_name",
                    models.CharField(
                        max_length=25, null=True, verbose_name="First Name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        max_length=25, null=True, verbose_name="Last Name"
                    ),
                ),
                (
                    "picture",
                    cloudinary.models.CloudinaryField(
                        blank=True,
                        max_length=255,
                        null=True,
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=["jpg", "jpeg", "png"]
                            )
                        ],
                        verbose_name="staff_profiles",
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        choices=[
                            ("", "--choose gender--"),
                            ("Male", "Male"),
                            ("Female", "Female"),
                        ],
                        max_length=6,
                        verbose_name="Gender",
                    ),
                ),
                (
                    "marital_status",
                    models.CharField(
                        choices=[
                            ("", "--select marital status--"),
                            ("Single", "Single"),
                            ("Married", "Married"),
                            ("Divorced", "Divorced"),
                            ("Widowed", "Widowed"),
                            ("In a domestic partnership", "In a domestic partnership"),
                        ],
                        max_length=30,
                    ),
                ),
                ("email", models.EmailField(max_length=254, verbose_name="Email")),
                (
                    "home_district",
                    models.CharField(
                        max_length=30, null=True, verbose_name="Home District"
                    ),
                ),
                (
                    "mobile_telephone",
                    phonenumber_field.modelfields.PhoneNumberField(
                        blank=True,
                        default="+256999999999",
                        max_length=128,
                        null=True,
                        region=None,
                        verbose_name="Mobile Telephone",
                    ),
                ),
                (
                    "date_started_work",
                    models.DateField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(
                                limit_value=datetime.date(2013, 1, 1)
                            )
                        ],
                        verbose_name="Start Date",
                    ),
                ),
                (
                    "department",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "--select department--"),
                            ("ACCOUNTS", "ACCOUNTS"),
                            ("PROGRAMS", "PROGRAMS"),
                            ("BUSINESS OPERATIONS", "BUSINESS OPERATIONS"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="Department",
                    ),
                ),
                (
                    "job_title",
                    models.CharField(
                        max_length=30, null=True, verbose_name="Job Title"
                    ),
                ),
                (
                    "is_departed",
                    models.BooleanField(
                        default=False, verbose_name="Is the Staff departed?"
                    ),
                ),
                (
                    "is_sponsored",
                    models.BooleanField(
                        default=False, verbose_name="Is the Staff sponsored?"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "staff_details",
                "managed": True,
            },
        ),
        migrations.CreateModel(
            name="StaffDeparture",
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
                    "departure_date",
                    models.DateField(
                        blank=True, null=True, verbose_name="Departure Date"
                    ),
                ),
                (
                    "departure_reason",
                    models.TextField(verbose_name="Reason for Departure"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="departures",
                        to="staff.staff",
                        verbose_name="Staff Information",
                    ),
                ),
            ],
            options={
                "verbose_name": "Staff Departure",
                "verbose_name_plural": "Staff Departures",
            },
        ),
    ]
