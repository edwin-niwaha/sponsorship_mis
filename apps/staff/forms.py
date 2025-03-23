from django import forms

from .models import Staff, StaffDeparture

# =================================== STAFF FORM ===================================
class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        exclude = ("is_departed", "is_sponsored")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "date_started_work": forms.DateInput(attrs={"type": "date"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "marital_status": forms.Select(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add validation styles and attributes
        for field in ["first_name", "last_name"]:
            self.fields[field].widget.attrs.update({"class": "form-control"})
        
        self.fields["picture"].widget = forms.FileInput(attrs={"accept": "image/*"})

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name", "")
        last_name = cleaned_data.get("last_name", "")

        if len(first_name) < 3:
            self.add_error("first_name", "First name must be at least 3 characters long.")

        if len(last_name) < 3:
            self.add_error("last_name", "Last name must be at least 3 characters long.")

        return cleaned_data

    def clean_picture(self):
        picture = self.cleaned_data.get("picture")
        
        if picture:
            # Handle CloudinaryResource format
            if hasattr(picture, "format") and picture.format.lower() not in ("jpg", "jpeg", "png"):
                raise forms.ValidationError("Please upload a valid image (jpg, jpeg, png).")

            # Handle size check (only if it's a standard file upload)
            if hasattr(picture, "size") and picture.size > 1500 * 1024:  # 1.5 MB
                raise forms.ValidationError("Image size should not exceed 1.5 MB.")

        return picture


# =================================== STAFF DEPATURE ===================================
class StaffDepartureForm(forms.ModelForm):
    class Meta:
        model = StaffDeparture
        exclude = ("staff",)
        widgets = {
            "departure_date": forms.DateInput(attrs={"type": "date"}),
            "departure_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }
