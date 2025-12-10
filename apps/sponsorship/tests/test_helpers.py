import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
import responses
from apps.sponsorship.models import MoMoTransaction
from apps.sponsorship.momo_prod import (
    create_access_token,
    request_to_pay,
    generate_uuid,
)  # Adjust for your helpers
from django.conf import settings


class HelperFunctionTests(TestCase):

    @responses.activate
    def test_create_access_token_success(self):
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/token/",
            json={"access_token": "fake_token"},
            status=200,
        )
        token = create_access_token("fake_user", "fake_key", "fake_sub_key")
        self.assertEqual(token, "fake_token")

    @responses.activate
    def test_create_access_token_failure(self):
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/token/",
            status=401,
        )
        token = create_access_token("fake_user", "fake_key", "fake_sub_key")
        self.assertIsNone(token)

    def test_generate_uuid(self):
        uuid_str = generate_uuid()
        self.assertTrue(len(uuid_str) == 36)  # Basic UUID check

    @responses.activate
    def test_request_to_pay_success(self):
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/v1_0/requesttopay",
            status=202,
            body="Success",
        )
        status, res_text = request_to_pay(
            "fake_token", "fake_sub_key", "256700000000", 10000, "fake_ref"
        )
        self.assertEqual(status, 202)
        self.assertEqual(res_text, "Success")

    @responses.activate
    def test_request_to_pay_failure(self):
        responses.add(
            responses.POST,
            "https://proxy.momoapi.mtn.com/collection/v1_0/requesttopay",
            status=400,
            body="Error",
        )
        status, res_text = request_to_pay(
            "fake_token", "fake_sub_key", "256700000000", 10000, "fake_ref"
        )
        self.assertEqual(status, 400)
