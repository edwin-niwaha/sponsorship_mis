from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.sponsor.models import Sponsor, SponsorFeedback, SponsorshipType


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.org",
    PROGS_ADMIN_EMAIL="programs@example.org",
    BOO_EMAIL="",
    ED_EMAIL="",
)
class SponsorFeedbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sponsor",
            email="sponsor@example.org",
            password="password123",
        )
        self.sponsor = Sponsor.objects.create(
            first_name="Test",
            last_name="Sponsor",
            gender="Male",
            email="sponsor@example.org",
            sponsorship_type=SponsorshipType.GENERAL_SUPPORT,
            expected_amt=0,
        )

    def test_sponsor_can_submit_feedback_from_portal(self):
        self.client.login(username="sponsor", password="password123")

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("submit_sponsor_feedback"),
                {
                    "subject": "Payment question",
                    "message": "Please confirm my latest support payment.",
                },
                follow=True,
            )

        feedback = SponsorFeedback.objects.get()
        self.assertRedirects(response, reverse("sponsor_portal"))
        self.assertEqual(feedback.sponsor, self.sponsor)
        self.assertEqual(feedback.submitted_by, self.user)
        self.assertEqual(feedback.status, SponsorFeedback.Status.NEW)
        self.assertEqual(feedback.email_error, "")
        self.assertIsNotNone(feedback.email_sent_at)
        self.assertEqual(len(mail.outbox), 2)
        internal_email, sponsor_confirmation = mail.outbox
        self.assertIn("Payment question", internal_email.subject)
        self.assertEqual(internal_email.to, ["programs@example.org"])
        self.assertEqual(sponsor_confirmation.subject, "We Have Received Your Feedback")
        self.assertEqual(sponsor_confirmation.to, ["sponsor@example.org"])
