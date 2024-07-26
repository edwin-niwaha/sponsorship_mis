from django.test import TestCase
from ..models import Child


class ChildModelTests(TestCase):
    def setUp(self):
        self.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth="2010-05-15",
            year_enrolled=2022,
        )

    def test_string_representation(self):
        self.assertEqual(str(self.child), "John Doe")
