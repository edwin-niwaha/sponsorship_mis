import datetime
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.management.base import BaseCommand
from django.conf import settings
from ...models import Staff


class Command(BaseCommand):
    help = "Send birthday email wishes to staff"

    def handle(self, *args, **kwargs):
        today = datetime.date.today()
        birthday_staff = Staff.objects.filter(
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
            is_departed=False,
        )

        if not birthday_staff.exists():
            self.stdout.write(self.style.WARNING("No birthdays today."))
            return

        for staff in birthday_staff:
            if staff.email:
                subject = f"🎉 Happy Birthday, {staff.first_name}!"

                # Render HTML email template
                html_content = render_to_string(
                    "sdms/staff/birthday_email.html", {"staff_name": staff.first_name}
                )

                # Create email with both plain text and HTML versions
                email = EmailMultiAlternatives(
                    subject, "Happy Birthday!", settings.EMAIL_HOST_USER, [staff.email]
                )
                email.attach_alternative(html_content, "text/html")

                try:
                    email.send()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Sent birthday email to {staff.first_name} ({staff.email})"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to send email to {staff.first_name}: {e}"
                        )
                    )
