from django import forms
from django.core.exceptions import ValidationError
from .models import Sponsor
from apps.child.models import (Child, )

# =================================== SPONSOR FORM ===================================

class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        exclude = ("is_departed", )
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

            "first_street_address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "second_street_address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            )
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