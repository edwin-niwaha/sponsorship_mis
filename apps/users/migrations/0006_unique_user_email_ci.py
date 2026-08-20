from django.db import migrations
from django.db.models import Count
from django.db.models.functions import Lower


def ensure_existing_emails_are_unique(apps, schema_editor):
    User = apps.get_model("auth", "User")
    duplicates = list(
        User.objects.exclude(email="")
        .annotate(normalized_email=Lower("email"))
        .values("normalized_email")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .values_list("normalized_email", flat=True)[:10]
    )
    if duplicates:
        raise RuntimeError(
            "Duplicate user emails must be resolved before this migration can run: "
            + ", ".join(duplicates)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_deviceinstallation"),
    ]

    operations = [
        migrations.RunPython(
            ensure_existing_emails_are_unique,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql=(
                "CREATE UNIQUE INDEX unique_auth_user_email_ci "
                "ON auth_user (LOWER(email)) WHERE email <> '';"
            ),
            reverse_sql="DROP INDEX IF EXISTS unique_auth_user_email_ci;",
        ),
    ]
