# Generated by Django 4.2.15 on 2024-12-21 17:01

import datetime
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("child", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="child",
            name="date_of_birth",
            field=models.DateField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=datetime.date(1900, 1, 1)
                    ),
                    django.core.validators.MaxValueValidator(
                        limit_value=datetime.date(2024, 12, 21)
                    ),
                ],
                verbose_name="Date of Birth",
            ),
        ),
        migrations.AlterField(
            model_name="child",
            name="registration_date",
            field=models.DateField(
                blank=True,
                default=datetime.date(2013, 1, 1),
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=datetime.date(2013, 1, 1)
                    ),
                    django.core.validators.MaxValueValidator(
                        limit_value=datetime.date(2024, 12, 21)
                    ),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="childdepart",
            name="depart_date",
            field=models.DateField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=datetime.date(2013, 1, 1)
                    ),
                    django.core.validators.MaxValueValidator(
                        limit_value=datetime.date(2024, 12, 21)
                    ),
                ],
                verbose_name="Departure Date",
            ),
        ),
        migrations.AlterField(
            model_name="childincident",
            name="incident_date",
            field=models.DateField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=datetime.date(2013, 1, 1)
                    ),
                    django.core.validators.MaxValueValidator(
                        limit_value=datetime.date(2024, 12, 21)
                    ),
                ],
                verbose_name="Incident Date",
            ),
        ),
    ]
