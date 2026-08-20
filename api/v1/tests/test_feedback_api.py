from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.users.models import Contact


class FeedbackApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="feedback-user",
            email="feedback@example.org",
            password="test-password-123",
        )
        self.client.force_authenticate(self.user)

    def test_authenticated_user_can_submit_feedback(self):
        response = self.client.post(
            "/api/v1/feedback/",
            {
                "name": "Feedback User",
                "email": "feedback@example.org",
                "message": "Please help me review my account details.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Contact.objects.get().name, "Feedback User")

    def test_feedback_message_must_be_descriptive(self):
        response = self.client.post(
            "/api/v1/feedback/",
            {
                "name": "Feedback User",
                "email": "feedback@example.org",
                "message": "Help",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Contact.objects.count(), 0)
