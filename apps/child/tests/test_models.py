from django.test import TestCase
from django.utils import timezone
from datetime import date

# Import the necessary models for testing
from ..models import Child


# Create your tests here.
class ChildModelTests(TestCase):
    def setUp(self):
        self.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth=date(2010, 1, 1),
            year_enrolled=2020,
            is_child_in_school=True,
            is_sponsored=False,
            is_father_alive="Yes",
            is_mother_alive="Yes",
        )

    def test_child_creation(self):
        self.assertEqual(self.child.full_name, "John Doe")
        self.assertEqual(self.child.gender, "Male")
        self.assertEqual(self.child.date_of_birth, date(2010, 1, 1))
        self.assertEqual(self.child.year_enrolled, 2020)
        self.assertEqual(self.child.is_child_in_school, True)
        self.assertEqual(self.child.is_sponsored, False)
        self.assertEqual(self.child.is_father_alive, "Yes")
        self.assertEqual(self.child.is_mother_alive, "Yes")

    def test_string_representation(self):
        self.assertEqual(str(self.child), "John Doe")
