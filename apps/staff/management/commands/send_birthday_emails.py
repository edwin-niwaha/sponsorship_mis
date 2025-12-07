import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand

from ...models import Staff

# class Command(BaseCommand):
#     help = "Send birthday email wishes to staff"

#     def handle(self, *args, **kwargs):
#         today = datetime.date.today()
#         birthday_staff = Staff.objects.filter(
#             date_of_birth__month=today.month,
#             date_of_birth__day=today.day,
#             is_departed=False,
#         )

#         if not birthday_staff.exists():
#             self.stdout.write(self.style.WARNING("No birthdays today."))
#             return

#         for staff in birthday_staff:
#             if staff.email:
#                 subject = f"🎉 Happy Birthday, {staff.first_name}!"

#                 # Render HTML email template
#                 html_content = f"""
#                 <html>
#                 <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; background-color: #f4f4f9; padding: 20px;">
#                     <div style="max-width: 600px; margin: auto; padding: 30px; border: 1px solid #ddd; border-radius: 12px; background-color: #ffffff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
#                     <h2 style="color: #2E86C1; text-align: center; font-size: 28px; margin-bottom: 20px; font-weight: bold;">
#                         Happy Birthday, {staff.first_name}!
#                     </h2>
#                     <p style="font-size: 18px; line-height: 1.6; color: #555;">
#                         Dear <strong>{staff.first_name}</strong>,
#                     </p>
#                     <p style="font-size: 16px; line-height: 1.6; color: #555;">
#                         On this special day, we want to take a moment to celebrate YOU! 🎉 Your hard work,
#                         dedication, and positive attitude make you an invaluable member of our team.
#                     </p>
#                     <p style="font-size: 16px; line-height: 1.6; color: #555;">
#                         May this year bring you continued success, happiness, and wonderful new opportunities.
#                         Thank you for everything you do at <strong>Pendeza Uganda</strong>. We're proud to have you with us!
#                     </p>
#                     <div style="text-align: center; margin: 40px 0; border-top: 2px solid #2E86C1; padding-top: 20px;">
#                         <p style="font-size: 18px; line-height: 1.6; color: #555;">
#                         Wishing you an amazing year ahead, filled with joy, growth, and achievements! 🎈
#                         </p>
#                     </div>
#                     <p style="color: #888; font-size: 14px; text-align: center; margin-top: 20px;">
#                         With warmest regards, <br />
#                         <strong style="color: #2E86C1;">The Pendeza Uganda Team</strong>
#                     </p>
#                     </div>
#                 </body>
#                 </html>
#                 """

#                 # Create email with both plain text and HTML versions
#                 email = EmailMultiAlternatives(
#                     subject, "Happy Birthday!", settings.EMAIL_HOST_USER, [staff.email]
#                 )
#                 email.attach_alternative(html_content, "text/html")

#                 try:
#                     email.send()
#                     self.stdout.write(
#                         self.style.SUCCESS(
#                             f"Sent birthday email to {staff.first_name} ({staff.email})"
#                         )
#                     )
#                 except Exception as e:
#                     self.stdout.write(
#                         self.style.ERROR(
#                             f"Failed to send email to {staff.first_name}: {e}"
#                         )
#                     )


class Command(BaseCommand):
    help = "Send professional birthday email wishes to current and former staff"

    def handle(self, *args, **kwargs):
        today = datetime.date.today()
        birthday_staff = Staff.objects.filter(
            date_of_birth__month=today.month, date_of_birth__day=today.day
        )

        if not birthday_staff.exists():
            self.stdout.write(self.style.WARNING("No staff birthdays today."))
            return

        for staff in birthday_staff:
            if not staff.email:
                continue

            first_name = staff.first_name
            org = "Pendeza Uganda"
            status = (
                "valued former colleague"
                if staff.is_departed
                else "esteemed team member"
            )

            subject = f"Happy Birthday, {first_name}!"
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; background-color: #f9f9fb; padding: 20px;">
                <div style="max-width: 600px; margin: auto; padding: 30px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                    <h2 style="color: #1a5d8c; text-align: center; font-size: 24px; margin-bottom: 20px; font-weight: 600;">
                        Happy Birthday, {first_name}
                    </h2>
                    <p style="font-size: 16px; line-height: 1.7; color: #444;">
                        Dear {first_name},
                    </p>
                    <p style="font-size: 15px; line-height: 1.7; color: #444;">
                        On behalf of the {org} team, we extend our warmest birthday wishes to you. 
                        Your dedication and contributions as our {status} continue to be deeply appreciated.
                    </p>
                    <p style="font-size: 15px; line-height: 1.7; color: #444; margin-bottom: 25px;">
                        May this new year of life bring you continued success, good health, and fulfillment.
                    </p>
                    <p style="color: #666; font-size: 14px; text-align: center; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
                        Best regards,<br>
                        <strong style="color: #1a5d8c;">The {org} Team</strong>
                    </p>
                </div>
            </body>
            </html>
            """

            email = EmailMultiAlternatives(
                subject, "Happy Birthday!", settings.EMAIL_HOST_USER, [staff.email]
            )
            email.attach_alternative(html_content, "text/html")
            try:
                email.send()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sent birthday email to {first_name} ({staff.email})"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to send email to {first_name}: {e}")
                )
