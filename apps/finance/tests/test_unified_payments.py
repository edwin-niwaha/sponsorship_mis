from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.finance.models import ChildPayments, Payment, SupportProgram
from apps.finance.services import (
    apply_sponsor_flags_for_program,
    get_one_time_only_donors,
    get_sponsor_portal_payment_summary,
)
from apps.sponsor.models import Sponsor, SponsorshipType


class UnifiedPaymentReportingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.child_support, _ = SupportProgram.objects.get_or_create(
            code=SupportProgram.CHILD_SUPPORT,
            defaults={"name": "Child Support"},
        )
        cls.one_time, _ = SupportProgram.objects.get_or_create(
            code=SupportProgram.ONE_TIME_DONATION,
            defaults={"name": "One-time Donation"},
        )
        cls.general_support, _ = SupportProgram.objects.get_or_create(
            code=SupportProgram.GENERAL_SUPPORT,
            defaults={"name": "General Support"},
        )

    def make_sponsor(self, email, sponsorship_type=""):
        return Sponsor.objects.create(
            first_name="Test",
            last_name="Supporter",
            gender="Male",
            email=email,
            sponsorship_type=sponsorship_type,
            expected_amt=0,
        )

    def test_real_supporters_excludes_only_one_time_donors(self):
        one_time_only = self.make_sponsor("one-time@example.org")
        one_time_only.is_one_time_donor = True
        one_time_only.save(update_fields=["is_one_time_donor"])
        Payment.objects.create(
            sponsor=one_time_only,
            program=self.one_time,
            amount=100,
            payment_date=date(2026, 1, 1),
        )

        child_sponsor = self.make_sponsor(
            "child-sponsor@example.org",
            sponsorship_type=SponsorshipType.CHILD_FULL_SUPPORT,
        )
        Payment.objects.create(
            sponsor=child_sponsor,
            program=self.child_support,
            amount=200,
            payment_date=date(2026, 1, 2),
        )

        real_supporters = Sponsor.objects.real_sponsors_only()

        self.assertIn(child_sponsor, real_supporters)
        self.assertNotIn(one_time_only, real_supporters)

    def test_sponsorship_type_sets_classification_flags(self):
        child_sponsor = self.make_sponsor(
            "flag-child@example.org",
            sponsorship_type=SponsorshipType.CHILD_FULL_SUPPORT,
        )
        general_donor = self.make_sponsor(
            "flag-general@example.org",
            sponsorship_type=SponsorshipType.GENERAL_SUPPORT,
        )

        self.assertTrue(child_sponsor.is_child_sponsor)
        self.assertFalse(child_sponsor.is_one_time_donor)
        self.assertTrue(general_donor.is_general_donor)
        self.assertIn(child_sponsor, Sponsor.objects.child_sponsors())
        self.assertIn(general_donor, Sponsor.objects.general_donors())

    def test_sponsor_with_real_support_and_one_time_donation_is_included(self):
        mixed_supporter = self.make_sponsor(
            "mixed@example.org",
            sponsorship_type=SponsorshipType.GENERAL_SUPPORT,
        )
        Payment.objects.create(
            sponsor=mixed_supporter,
            program=self.general_support,
            amount=150,
            payment_date=date(2026, 1, 3),
        )
        Payment.objects.create(
            sponsor=mixed_supporter,
            program=self.one_time,
            amount=50,
            payment_date=date(2026, 1, 4),
        )

        self.assertIn(mixed_supporter, Sponsor.objects.real_sponsors_only())
        self.assertNotIn(mixed_supporter, get_one_time_only_donors())

    def test_payment_queryset_one_time_only_returns_only_exclusive_donor_payments(self):
        one_time_only = self.make_sponsor("only@example.org")
        mixed_supporter = self.make_sponsor("mixed-payments@example.org")

        exclusive_payment = Payment.objects.create(
            sponsor=one_time_only,
            program=self.one_time,
            amount=100,
            payment_date=date(2026, 1, 5),
        )
        Payment.objects.create(
            sponsor=mixed_supporter,
            program=self.one_time,
            amount=75,
            payment_date=date(2026, 1, 6),
        )
        Payment.objects.create(
            sponsor=mixed_supporter,
            program=self.general_support,
            amount=125,
            payment_date=date(2026, 1, 7),
        )

        self.assertQuerySetEqual(
            Payment.objects.one_time_only(),
            [exclusive_payment],
            transform=lambda payment: payment,
        )

    def test_sponsor_portal_summary_captures_other_and_one_time_payments(self):
        sponsor = self.make_sponsor(
            "portal@example.org",
            sponsorship_type=SponsorshipType.GENERAL_SUPPORT,
        )
        Payment.objects.create(
            sponsor=sponsor,
            program=self.general_support,
            amount=300,
            payment_date=date(2026, 2, 1),
        )
        Payment.objects.create(
            sponsor=sponsor,
            program=self.one_time,
            amount=25,
            payment_date=date(2026, 2, 2),
        )

        summary = get_sponsor_portal_payment_summary(sponsor)

        self.assertTrue(summary["has_unified_payments"])
        self.assertEqual(summary["total_payment_amount"], Decimal("325"))
        self.assertEqual(summary["real_support_total"], Decimal("300"))
        self.assertEqual(summary["other_payment_total"], Decimal("300"))
        self.assertEqual(summary["one_time_payment_total"], Decimal("25"))
        self.assertEqual(len(summary["recent_payments"]), 2)
        categories = {item["key"]: item for item in summary["payment_categories"]}
        self.assertTrue(categories["general-support"]["has_payments"])
        self.assertTrue(categories["one-time-donation"]["has_payments"])
        self.assertFalse(categories["family-support"]["has_payments"])

    def test_sponsor_level_payment_program_sets_matching_flag(self):
        sponsor = self.make_sponsor("family-support@example.org")
        family_support, _ = SupportProgram.objects.get_or_create(
            code=SupportProgram.FAMILY_SUPPORT,
            defaults={"name": "Family Full Support"},
        )

        apply_sponsor_flags_for_program(sponsor, family_support)
        sponsor.refresh_from_db()

        self.assertTrue(sponsor.is_family_supporter)
        self.assertFalse(sponsor.is_one_time_donor)

    def test_portal_summary_keeps_legacy_child_payments_when_unified_other_payments_exist(
        self,
    ):
        sponsor = self.make_sponsor(
            "mixed-legacy@example.org",
            sponsorship_type=SponsorshipType.CHILD_FULL_SUPPORT,
        )
        ChildPayments.objects.create(
            sponsor=sponsor,
            child=None,
            payment_date=date(2026, 3, 1),
            month="March",
            payment_year=2026,
            amount=400,
            is_valid=True,
        )
        Payment.objects.create(
            sponsor=sponsor,
            program=self.general_support,
            amount=125,
            payment_date=date(2026, 3, 2),
        )

        summary = get_sponsor_portal_payment_summary(sponsor)
        categories = {item["key"]: item for item in summary["payment_categories"]}

        self.assertEqual(summary["total_payment_amount"], Decimal("525"))
        self.assertEqual(categories["child-support"]["amount"], Decimal("400"))
        self.assertTrue(categories["child-support"]["has_legacy_payments"])
        self.assertEqual(categories["general-support"]["amount"], Decimal("125"))
