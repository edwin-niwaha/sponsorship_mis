from django import forms

from .models import Sponsor, SponsorDeparture


# =================================== SPONSOR FORM ===================================
class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        exclude = ("is_departed",)
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
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
