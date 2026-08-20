import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0004_profile_account_type_profile_sponsor_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceInstallation",
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
                ("installation_id", models.UUIDField()),
                ("push_token", models.CharField(max_length=512)),
                (
                    "platform",
                    models.CharField(
                        choices=[("android", "Android"), ("ios", "iOS")],
                        max_length=10,
                    ),
                ),
                ("app_version", models.CharField(blank=True, max_length=32)),
                ("notifications_enabled", models.BooleanField(default=True)),
                ("active", models.BooleanField(default=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="device_installations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="deviceinstallation",
            constraint=models.UniqueConstraint(
                fields=("user", "installation_id"),
                name="unique_user_device_installation",
            ),
        ),
        migrations.AddIndex(
            model_name="deviceinstallation",
            index=models.Index(fields=["user", "active"], name="users_devic_user_id_eeac14_idx"),
        ),
        migrations.AddIndex(
            model_name="deviceinstallation",
            index=models.Index(fields=["push_token"], name="users_devic_push_to_f8b98d_idx"),
        ),
    ]
