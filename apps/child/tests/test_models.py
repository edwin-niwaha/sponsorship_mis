from django.core.files.storage import default_storage
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
import datetime
from django.core.exceptions import ValidationError

# Import the necessary models for testing
from ..models import (
    Child,
    ChildProfilePicture,
    ChildProgress,
    ChildCorrespondence,
    ChildIncident,
)


# =================================== TEST CHILD MODEL ===================================
class ChildModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.valid_image = SimpleUploadedFile(
            name="test_image.jpg", content=b"", content_type="image/jpeg"
        )
        cls.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth=datetime.date(2010, 5, 15),
            picture=cls.valid_image,
            year_enrolled=2020,
            is_departed=False,
        )

    def test_full_name_validation(self):
        invalid_names = [
            "John123",
            "John Doe!",
            "John@Doe",
        ]
        for name in invalid_names:
            with self.assertRaises(ValidationError):
                child = Child(full_name=name, gender="Male")
                child.full_clean()  # This will trigger validation

    def test_date_of_birth_validations(self):
        future_date = datetime.date.today() + datetime.timedelta(days=1)
        past_date = datetime.date(1899, 12, 31)

        child_future = Child(
            full_name="Jane Doe",
            gender="Female",
            date_of_birth=future_date,
        )
        child_past = Child(
            full_name="Jane Doe",
            gender="Female",
            date_of_birth=past_date,
        )

        with self.assertRaises(ValidationError):
            child_future.full_clean()  # This will trigger validation

        with self.assertRaises(ValidationError):
            child_past.full_clean()  # This will trigger validation

    def test_picture_field_validation(self):
        invalid_image = SimpleUploadedFile(
            name="test_image.txt", content=b"", content_type="text/plain"
        )

        child_invalid_image = Child(
            full_name="Alice Doe",
            gender="Female",
            picture=invalid_image,
            year_enrolled=2021,
        )

        with self.assertRaises(ValidationError):
            child_invalid_image.full_clean()  # This will trigger validation

    def test_default_values(self):
        child = Child.objects.create(
            full_name="Default Test",
            gender="Male",
            date_of_birth=datetime.date(2010, 1, 1),
            year_enrolled=2021,
        )

        self.assertFalse(child.is_child_in_school)
        self.assertFalse(child.is_sponsored)
        self.assertFalse(child.is_departed)
        self.assertEqual(child.picture.name, "default.jpg")

    def test_calculate_age(self):
        child = Child(
            full_name="Age Test",
            gender="Male",
            date_of_birth=datetime.date(2010, 1, 1),
            year_enrolled=2021,
        )
        age = child.calculate_age()
        today = datetime.date.today()
        expected_age = today.year - 2010 - ((today.month, today.day) < (1, 1))
        self.assertEqual(age, expected_age)

    def test_prefixed_id(self):
        self.assertEqual(self.child.prefixed_id, f"CH0{self.child.pk}")

    def test_str_method(self):
        self.assertEqual(str(self.child), "John Doe")

    def test_field_labels(self):
        child = Child()
        field_labels = {
            "full_name": "Full Name",
            "preferred_name": "Preferred Name",
            "residence": "Current Residence",
            "district": "Home District",
            "tribe": "Tribe",
            "gender": "Gender",
            "date_of_birth": "Date of Birth",
            "picture": "Upload Image(jpg, jpeg, png)",
            "weight": "Weight in kilograms",
            "height": "Height in centimeters",
            "aspiration": "Aspiration",
            "c_interest": "Interest and abilities ",
            "is_child_in_school": "Is the Child in School?",
            "is_sponsored": "Is the Child sponsored?",
            "father_name": "Father’s Name",
            "is_father_alive": "Is the father alive?",
            "father_description": "if not what happened/if alive what is happening?",
            "mother_name": "Mother’s name",
            "is_mother_alive": "is the mother alive?",
            "mother_description": "if not what happened/if alive what is happening?",
            "guardian": "Current guardian",
            "guardian_contact": "Guardian Contact",
            "relationship_with_guardian": "Relationship with the Guardian",
            "siblings": "List names and age of the siblings",
            "background_info": "Other family back ground information",
            "health_status": "General health status",
            "responsibility": "Child’s responsibilities",
            "relationship_with_christ": "Relationship with Christ",
            "religion": "Religion of the Child",
            "prayer_request": "Prayer needs/request",
            "year_enrolled": "The year when the child was enrolled on the program?",
            "is_departed": "Is the Child departed?",
            "staff_comment": "Staff Comment ",
            "compiled_by": "Compiled by",
            "created_at": "Created at",
            "updated_at": "Updated at",
        }
        for field_name, label in field_labels.items():
            self.assertEqual(child._meta.get_field(field_name).verbose_name, label)


# =================================== TEST CHILD PROFILE PICTURES MODEL ===================================
class ChildProfilePictureModelTest(TestCase):

    def setUp(self):
        # Create a test Child instance
        self.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth="2010-01-01",
            year_enrolled=2021,
        )

        # Create a test ChildProfilePicture instance
        self.profile_picture = ChildProfilePicture.objects.create(
            child=self.child, uploaded_at=timezone.now()
        )

    def test_str_method(self):
        # Ensure the string representation of ProfilePicture is correct
        expected_str = f"Profile picture of {self.child.full_name} uploaded at {self.profile_picture.uploaded_at}"
        self.assertEqual(str(self.profile_picture), expected_str)

    def test_field_labels(self):
        # Example test for field labels
        field_labels = {
            "child": "Child",
            "uploaded_at": "Uploaded at",
        }
        for field_name, label in field_labels.items():
            self.assertEqual(
                self.profile_picture._meta.get_field(field_name).verbose_name, label
            )

    def test_uploaded_at_default(self):
        # Ensure the `uploaded_at` field has a default value
        self.assertIsNotNone(self.profile_picture.uploaded_at)


# =================================== TEST CHILD PROGRESS MODEL ===================================
class ChildProgressModelTest(TestCase):

    def setUp(self):
        # Create a test Child instance
        self.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth="2010-01-01",
            year_enrolled=2021,
        )

        # Create a test ChildProgress instance
        self.child_progress = ChildProgress.objects.create(
            child=self.child,
            name_of_school="Springfield Elementary",
            previous_schools="None",
            education_level="Primary",
            child_class="P.4",
            best_subject="Mathematics",
            score=0,
            co_curricular_activity="Football",  # Provided value
            responsibility_at_school="Class Monitor",
            future_plans="Become an Engineer",
            responsibility_at_home="Helping with chores",
            notes="Good progress",
        )

    def test_str_method(self):
        # Expected string representation
        expected_str = f"{self.child.full_name} - {self.child_progress.name_of_school}"
        # Verify the __str__ method
        self.assertEqual(str(self.child_progress), expected_str)

    def test_field_labels(self):
        # Check verbose names for fields
        field_labels = {
            "child": "Child",
            "name_of_school": "Name of the School",
            "previous_schools": "Previous Schools Attended",
            "education_level": "Level of Education",
            "child_class": "Class",
            "best_subject": "Best Subject",
            "score": "Score",
            "co_curricular_activity": "Co-curricular Activity (Optional)",
            "responsibility_at_school": "Responsibility at School (Optional)",
            "future_plans": "Future Plans",
            "responsibility_at_home": "Responsibility at Home (Optional)",
            "notes": "Notes (Optional)",
            "created_at": "Created at",
            "updated_at": "Updated at",
        }
        for field_name, label in field_labels.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    self.child_progress._meta.get_field(field_name).verbose_name, label
                )

    def test_default_values(self):
        # Test default values for optional fields
        new_child_progress = ChildProgress.objects.create(
            child=self.child,
            name_of_school="Test School",
            education_level="Primary",
            child_class="P.1",
            best_subject="Science",
            future_plans="Become a Scientist",
        )
        self.assertEqual(new_child_progress.score, 0)  # Default value for score
        self.assertIsNone(
            new_child_progress.co_curricular_activity
        )  # Default value for optional fields
        self.assertIsNone(
            new_child_progress.responsibility_at_school
        )  # Default value for optional fields
        self.assertIsNone(
            new_child_progress.responsibility_at_home
        )  # Default value for optional fields
        self.assertIsNone(new_child_progress.notes)  # Default value for optional fields

    def test_creation_and_update(self):
        # Verify that the model instance is created and updated correctly
        self.assertEqual(self.child_progress.child, self.child)
        self.assertEqual(self.child_progress.name_of_school, "Springfield Elementary")
        self.assertEqual(self.child_progress.education_level, "Primary")
        self.assertEqual(self.child_progress.child_class, "P.4")
        self.assertEqual(self.child_progress.best_subject, "Mathematics")
        self.assertEqual(self.child_progress.score, 0)
        self.assertEqual(self.child_progress.co_curricular_activity, "Football")
        self.assertEqual(self.child_progress.responsibility_at_school, "Class Monitor")
        self.assertEqual(self.child_progress.future_plans, "Become an Engineer")
        self.assertEqual(
            self.child_progress.responsibility_at_home, "Helping with chores"
        )
        self.assertEqual(self.child_progress.notes, "Good progress")

        # Update the instance and verify changes
        self.child_progress.name_of_school = "New School"
        self.child_progress.save()
        self.child_progress.refresh_from_db()
        self.assertEqual(self.child_progress.name_of_school, "New School")


# =================================== TEST CHILD CORRESPONDENCE MODEL ===================================
class ChildCorrespondenceModelTest(TestCase):

    def setUp(self):
        self.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth="2010-01-01",
            year_enrolled=2021,
        )
        self.attachment = SimpleUploadedFile("file.txt", b"file_content")

    def test_create_child_correspondence(self):
        correspondence = ChildCorrespondence.objects.create(
            child=self.child,
            correspondence_type="Letter",
            source="CHILD",
            attachment=self.attachment,
            comment="This is a test comment",
        )
        # Check if the attachment is not None
        self.assertIsNotNone(correspondence.attachment)

        # Get the file path
        attachment_path = correspondence.attachment.name

        # Print the file path for debugging
        print(f"Attachment path: {attachment_path}")

        # Check if the file exists in the storage
        self.assertTrue(
            default_storage.exists(attachment_path),
            f"Expected file path to exist: {attachment_path}",
        )

        self.assertEqual(correspondence.child, self.child)
        self.assertEqual(correspondence.correspondence_type, "Letter")
        self.assertEqual(correspondence.source, "CHILD")
        self.assertEqual(correspondence.comment, "This is a test comment")
        self.assertIsNotNone(correspondence.created_at)
        self.assertIsNotNone(correspondence.updated_at)

    def test_str_method(self):
        correspondence = ChildCorrespondence.objects.create(
            child=self.child, correspondence_type="Letter", source="CHILD"
        )
        self.assertEqual(str(correspondence), f"{self.child} - Letter")

    def test_blank_comment(self):
        correspondence = ChildCorrespondence.objects.create(
            child=self.child, correspondence_type="Letter", source="CHILD", comment=""
        )
        self.assertEqual(correspondence.comment, "")

    def test_null_attachment(self):
        correspondence = ChildCorrespondence.objects.create(
            child=self.child,
            correspondence_type="Letter",
            source="CHILD",
            attachment=None,
        )

        # Check if the attachment is not present or is an empty FieldFile
        self.assertFalse(
            correspondence.attachment,
            "Expected attachment to be an empty FieldFile or None",
        )

    def test_default_choice_values(self):
        correspondence = ChildCorrespondence.objects.create(
            child=self.child,
            correspondence_type="Letter",
            source="CHILD",
        )
        # Assuming `correspondence_type` and `source` are choices in the model,
        # you should test default values if they are set in the model itself.
        self.assertEqual(correspondence.correspondence_type, "Letter")
        self.assertEqual(correspondence.source, "CHILD")


# =================================== TEST CHILD INCIDENT MODEL ===================================
class IncidentModelTest(TestCase):

    def setUp(self):
        # Create a Child instance
        self.child = Child.objects.create(
            full_name="John Doe",
            gender="Male",
            date_of_birth="2010-01-01",
            year_enrolled=2021,
        )
        # Create an Incident instance
        self.incident = ChildIncident.objects.create(
            child=self.child,
            incident_date="2024-07-30",
        )

    def test_str_method(self):
        # Expected string representation
        expected_str = (
            f"Incident of {self.child.full_name} on {self.incident.incident_date}"
        )

        # Assert that the __str__ method returns the expected string
        self.assertEqual(str(self.incident), expected_str)
