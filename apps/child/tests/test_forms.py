from django.test import TestCase
from django import forms

# Import the necessary forms for testing
from apps.child.forms import ChildForm


# =================================== TEST CHILD FORM ===================================
class ChildFormTest(TestCase):
    def test_widgets(self):
        form = ChildForm()

        # Check checkbox widget and attribute
        self.assertIsInstance(
            form.fields["is_child_in_school"].widget, forms.CheckboxInput
        )
        self.assertEqual(
            form.fields["is_child_in_school"].widget.attrs["class"], "form-control"
        )

    ### 2. Testing Form Validation
    def test_full_name_validation(self):
        form_data = {"full_name": "Jo", "preferred_name": "John"}
        form = ChildForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)
        self.assertEqual(
            form.errors["full_name"],
            ["Can not save first name less than 3 characters long"],
        )

    def test_preferred_name_validation(self):
        form_data = {"full_name": "John Doe", "preferred_name": "Jo"}
        form = ChildForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("preferred_name", form.errors)
        self.assertEqual(
            form.errors["preferred_name"],
            ["Can not save last name less than 3 characters long"],
        )


def test_valid_form(self):
    form_data = {
        "full_name": "John Doe",
        "preferred_name": "John",
        "date_of_birth": "2010-01-01",
        "siblings": "None",
        "background_info": "Info",
        "responsibility": "None",
        "mother_description": "Description",
        "staff_comment": "Comment",
        "father_description": "Description",
        "c_interest": "Interest",
        "gender": "Male",
        "is_father_alive": "Yes",
        "is_mother_alive": "Yes",
        "religion": "Religion",
        "is_child_in_school": True,
    }
    form = ChildForm(data=form_data)
    if not form.is_valid():
        print("Form errors:", form.errors)
    self.assertTrue(form.is_valid())
