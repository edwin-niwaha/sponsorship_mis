from django import forms
from django.core.exceptions import ValidationError

from .models import Child, ChildCorrespondence, ChildIncident, ChildProfilePicture, ChildProgress


class UploadForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = "__all__"
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "siblings": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "background_info": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "responsibility": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "mother_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "staff_comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "father_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "c_interest": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    # Form validation
    def clean(self):
        super(ChildForm, self).clean()

        full_name = self.cleaned_data.get("full_name")
        preferred_name = self.cleaned_data.get("preferred_name")

        if len(full_name) < 3:
            self.add_error(
                "full_name", "Can not save first name less than 3 characters long"
            )
            self.fields["full_name"].widget.attrs.update(
                {"class": "form-control  is-invalid"}
            )

        if len(preferred_name) < 3:
            self.add_error(
                "preferred_name", "Can not save last name less than 3 characters long"
            )
            self.fields["preferred_name"].widget.attrs.update(
                {"class": "form-control  is-invalid"}
            )

        return self.cleaned_data


class ChildProfilePictureForm(forms.ModelForm):
    class Meta:
        model = ChildProfilePicture
        fields = ["picture"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["picture"].widget = forms.FileInput(attrs={"accept": "image/*"})

    def clean_picture(self):
        picture = self.cleaned_data.get("picture")
        return picture

class ChildProgressForm(forms.ModelForm):
    class Meta:
        model = ChildProgress
        exclude = ("child", )
        widgets = {
            "previous_schools": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "future_plans": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "responsibility_at_home": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "education_level": forms.Select(attrs={'class': 'form-select'}),
            "child_class": forms.Select(attrs={'class': 'form-select'}),
        }

class ChildCorrespondenceForm(forms.ModelForm):
    class Meta:
        model = ChildCorrespondence
        exclude = ("child", )
        widgets = {
            'correspondence_type': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control-file'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            # 'sponsor': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if not attachment:
            raise ValidationError("Attachment is required for all correspondence.")
        
        # Check if the attachment is a PDF file
        if not attachment.name.endswith('.pdf'):
            raise ValidationError("Only PDF attachments are allowed.")
        
        return attachment


class ChildIncidentForm(forms.ModelForm):
    class Meta:
        model = ChildIncident
        exclude = ("child", )
        widgets = {
            "incident_date": forms.DateInput(attrs={"type": "date"}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'attachment': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if not attachment:
            raise ValidationError("Attachment is required.")
        
        # Check if the attachment is a PDF file
        if not attachment.name.lower().endswith('.pdf'):
            raise ValidationError("Only PDF attachments are allowed.")
        
        return attachment