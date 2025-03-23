from django import forms

from .models import Staff, StaffDeparture

# =================================== STAFF FORM ===================================


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        exclude = ("is_departed", "is_sponsored")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "required": True}),
            "date_started_work": forms.DateInput(
                attrs={"type": "date", "required": True}
            ),
            "gender": forms.Select(attrs={"class": "form-control", "required": True}),
            "marital_status": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "department": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
        }

    # Form validation
    def clean(self):
        super(StaffForm, self).clean()

        first_name = self.cleaned_data.get("first_name")
        last_name = self.cleaned_data.get("last_name")

        if len(first_name) < 3:
            self.add_error(
                "first_name", "Can not save first name less than 3 characters long"
            )
            self.fields["first_name"].widget.attrs.update(
                {"class": "form-control  is-invalid"}
            )

        if len(last_name) < 3:
            self.add_error(
                "last_name", "Can not save last name less than 3 characters long"
            )
            self.fields["last_name"].widget.attrs.update(
                {"class": "form-control  is-invalid"}
            )

        return self.cleaned_data


class StaffUpdateForm(forms.ModelForm):
    class Meta:
        model = Staff
        exclude = ("is_departed", "is_sponsored", "created_at", "updated_at")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "required": True}),
            "date_started_work": forms.DateInput(
                attrs={"type": "date", "required": True}
            ),
            "gender": forms.Select(attrs={"class": "form-control", "required": True}),
            "marital_status": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "department": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
        }

    def clean_picture(self):
        picture = self.cleaned_data.get('picture')
        if picture:
            # You can add any custom validation here if needed
            if not picture.name.endswith(('jpg', 'jpeg', 'png')):
                raise forms.ValidationError("Please upload a valid image (jpg, jpeg, png).")
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
