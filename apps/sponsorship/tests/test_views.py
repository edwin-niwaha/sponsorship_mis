import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
import responses

from apps.sponsorship.models import MoMoTransaction
from apps.users.models import Profile


class ViewTests(TestCase):

    def setUp(self):
        self.client = Client()

        # -----------------------------
        # Create authorized admin user
        # -----------------------------
        self.admin_user = User.objects.create_user(username="admin", password="pass123")
        Profile.objects.create(user=self.admin_user, role="administrator")

        # Login as admin
        self.client.login(username="admin", password="pass123")

        # -----------------------------
        # Patch MoMo Settings
        # -----------------------------
        self.settings_patch = patch.multiple(
            "django.conf.settings",
            MOMO_API_USER="fake_user",
            MOMO_API_KEY="fake_key",
            SUBSCRIPTION_KEY="fake_sub_key",
            MOMO_CALLBACK_URL="http://fake/callback",
        )
        self.settings_patch.start()

        # -----------------------------
        # Default POST data
        # -----------------------------
        self.valid_post_data = {
            "phone": "0701234567",
            "amount": "10000",
            "name": "Test Donor",
            "email": "test@example.com",
        }

    def tearDown(self):
        self.settings_patch.stop()

    # ==============================
    # Initiate Payment View Tests
    # ==============================
    @responses.activate
    def test_initiate_payment_get(self):
        response = self.client.get(reverse("initiate_payment"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sponsorship/initiate_payment.html")

    @responses.activate
    def test_initiate_payment_post_success(self):
        # Mock token
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/token/",
            json={"access_token": "fake"},
            status=200,
        )
        # Mock request-to-pay
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/v1_0/requesttopay",
            status=202,
        )

        response = self.client.post(reverse("initiate_payment"), self.valid_post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("waiting")))

    @responses.activate
    def test_initiate_payment_post_invalid_phone(self):
        data = self.valid_post_data.copy()
        data["phone"] = "invalid"

        response = self.client.post(reverse("initiate_payment"), data)
        self.assertEqual(response.status_code, 200)

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Invalid phone number.", messages)

    # ==============================
    # Waiting View Tests
    # ==============================
    def test_waiting_get_success(self):
        query = "?ref=fake_ref&amount=10000&phone=0701234567&name=Test&email=test@example.com"
        response = self.client.get(reverse("waiting") + query)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sponsorship/waiting.html")
        self.assertEqual(response.context["transaction_id"], "fake_ref")

    def test_waiting_get_missing_params(self):
        response = self.client.get(reverse("waiting"))
        self.assertRedirects(response, reverse("initiate_payment"))

    # ==============================
    # Transaction Status API Tests
    # ==============================
    @responses.activate
    def test_get_transaction_status_success(self):
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/token/",
            json={"access_token": "fake"},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://proxy.momoapi.mtn.com/collection/v1_0/requesttopay/fake_ref",
            json={"status": "SUCCESSFUL"},
            status=200,
        )

        response = self.client.get(reverse("transaction_status", args=["fake_ref"]))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "SUCCESSFUL")

    # ==============================
    # Callback View Tests
    # ==============================
    def test_momo_callback_invalid_method(self):
        response = self.client.get(reverse("momo_callback"))
        self.assertEqual(response.status_code, 405)

    def test_momo_callback_success_update(self):
        txn = MoMoTransaction.objects.create(
            reference_id="fake_ref",
            external_id="fake_ext",
            status="PENDING",
            amount=10000,
        )

        payload = json.dumps(
            {"externalId": "fake_ext", "status": "SUCCESSFUL", "amount": "10000"}
        )

        response = self.client.post(
            reverse("momo_callback"), data=payload, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        txn.refresh_from_db()
        self.assertEqual(txn.status, "SUCCESSFUL")

    def test_momo_callback_invalid_json(self):
        response = self.client.post(
            reverse("momo_callback"), data="notjson", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    # ==============================
    # Thank You Page Tests
    # ==============================
    def test_thank_you_get_success(self):
        txn = MoMoTransaction.objects.create(
            reference_id="fake_ref",
            phone_number="0701234567",
            amount=10000,
            status="SUCCESSFUL",
        )

        query = f"?ref={txn.reference_id}&amount={txn.amount}&phone={txn.phone_number}&name=Test&email=test@example.com"
        response = self.client.get(reverse("thank_you") + query)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sponsorship/thank_you.html")

    # ==============================
    # Transaction List View Tests
    # ==============================
    def test_momo_transaction_list_get_authorized(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("momo_transaction_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sponsorship/momo_trans_list.html")

    def test_momo_transaction_list_get_unauthorized(self):
        self.client.logout()

        response = self.client.get(reverse("momo_transaction_list"))
        self.assertEqual(response.status_code, 302)  # redirect to login
