from django.core.management.base import BaseCommand

from apps.finance.models import SupportProgram


class Command(BaseCommand):
    help = "Create default support programs"

    def handle(self, *args, **options):
        programs = [
            ("Child Support", SupportProgram.CHILD_SUPPORT),
            ("Child Co-support", SupportProgram.CHILD_CO_SUPPORT),
            ("Family Support", SupportProgram.FAMILY_SUPPORT),
            ("Family Co-support", SupportProgram.FAMILY_CO_SUPPORT),
            ("General Support", SupportProgram.GENERAL_SUPPORT),
            ("Staff Support", SupportProgram.STAFF_SUPPORT),
            ("One-time Donation", SupportProgram.ONE_TIME_DONATION),
        ]

        for name, code in programs:
            obj, created = SupportProgram.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))
            elif obj.name != name:
                obj.name = name
                obj.is_active = True
                obj.save(update_fields=["name", "is_active"])
                self.stdout.write(self.style.WARNING(f"Updated: {name}"))
            else:
                self.stdout.write(f"Already exists: {name}")
