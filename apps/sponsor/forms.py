from django import forms

from .models import Donor, Sponsor, SponsorDeparture


# =================================== SPONSOR FORM ===================================
class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        exclude = ("is_departed",)
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "first_street_address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "second_street_address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "gender": forms.Select(attrs={"class": "form-control", "required": True}),
            "sponsorship_type_at_signup": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
        }

    # Form validation
    def clean(self):
        super(SponsorForm, self).clean()

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


# =================================== DONOR FORM ===================================
class DonorForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = ["full_name", "email", "phone"]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Full Name",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone Number"}
            ),
        }


# =================================== SPONSOR DEPATURE ===================================
class SponsorDepartForm(forms.ModelForm):
    class Meta:
        model = SponsorDeparture
        exclude = ("sponsor",)
        widgets = {
            "departure_date": forms.DateInput(attrs={"type": "date"}),
            "departure_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }


# =================================== SPONSOR upload ===================================


class SponsorUploadForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"
