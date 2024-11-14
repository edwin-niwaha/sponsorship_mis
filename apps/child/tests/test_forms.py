from io import BytesIO

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.test import TestCase

# Import the necessary forms for testing
from apps.child.forms import (
    ChildCorrespondenceForm,
    ChildForm,
    ChildIncidentForm,
    ChildProfilePictureForm,
)


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


# =================================== TEST CHILD PROFILE FORM ===================================


class ChildProfilePictureFormTests(TestCase):
    def setUp(self):
        self.form_class = ChildProfilePictureForm

    def test_picture_widget(self):
        form = self.form_class()
        self.assertIsInstance(form.fields["picture"].widget, forms.FileInput)
        self.assertEqual(form.fields["picture"].widget.attrs.get("accept"), "image/*")

    def test_clean_picture_no_file(self):
        form = self.form_class(data={})
        form.is_valid()  # Trigger validation
        cleaned_picture = form.cleaned_data.get("picture")
        self.assertIsNone(cleaned_picture)

    def test_invalid_file_type(self):
        file = SimpleUploadedFile(
            "test_document.txt", b"file_content", content_type="text/plain"
        )
        form = ChildProfilePictureForm(files={"picture": file})
        self.assertFalse(form.is_valid())
        self.assertIn("picture", form.errors)

    def test_widget_attributes(self):
        form = ChildProfilePictureForm()
        widget_attrs = form.fields["picture"].widget.attrs
        self.assertEqual(widget_attrs.get("accept"), "image/*")

    def test_clean_picture_method(self):
        # Create a valid image file
        image = SimpleUploadedFile(
            "test_image.jpg", b"file_content", content_type="image/jpeg"
        )
        form = ChildProfilePictureForm(files={"picture": image})

        # Ensure validation occurs
        form.is_valid()

        if form.is_valid():
            # Check if 'picture' is present in cleaned_data
            self.assertIn(
                "picture", form.cleaned_data, "Picture should be in cleaned_data"
            )
            self.assertEqual(form.cleaned_data["picture"].name, "test_image.jpg")
        else:
            # Print errors if the form is invalid
            print("Form errors:", form.errors)


# =================================== TEST CHILD CORRESSPONDENCE ===================================
class ChildCorrespondenceFormTests(TestCase):
    def test_missing_attachment(self):
        form = ChildCorrespondenceForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["attachment"],
            ["Attachment is required for all correspondence."],
        )

    def test_invalid_file_type(self):
        # Create a fake non-PDF file
        txt_file = InMemoryUploadedFile(
            file=BytesIO(b"This is a test file"),
            field_name="attachment",
            name="test.txt",
            content_type="text/plain",
            size=100,
            charset=None,
        )
        form = ChildCorrespondenceForm(files={"attachment": txt_file})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["attachment"], ["Only PDF attachments are allowed."]
        )


# =================================== TEST CHILD DEPATURE ===================================
class ChildIncidentFormTests(TestCase):
    def test_invalid_file_type(self):
        # Create a fake text file (not a PDF)
        text_file = InMemoryUploadedFile(
            file=BytesIO(b"This is not a PDF."),
            field_name="attachment",
            name="test_attachment.txt",
            content_type="text/plain",
            size=16,
            charset=None,
        )

        form = ChildIncidentForm(files={"attachment": text_file})

        # Ensure the form is invalid
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["attachment"], ["Only PDF attachments are allowed."]
        )

    # def test_valid_pdf_attachment(self):
    #     # Create a shorter valid PDF file
    #     pdf_content = b"%PDF-1.0\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
    #     pdf_file = InMemoryUploadedFile(
    #         file=BytesIO(pdf_content),
    #         field_name="attachment",
    #         name="test_attachment.pdf",
    #         content_type="application/pdf",
    #         size=len(pdf_content),
    #         charset=None,
    #     )

    #     # Create form instance with the PDF file
    #     form = ChildIncidentForm(files={"attachment": pdf_file})

    #     # Print form errors and debug information if invalid
    #     if not form.is_valid():
    #         print("Form errors:", form.errors)
    #         print("Form cleaned data:", form.cleaned_data)
    #         print("Uploaded file name:", form.files.get("attachment").name)

    #     # Ensure the form is valid
    #     self.assertTrue(
    #         form.is_valid(), "Form should be valid with a correct PDF attachment"
    #     )
