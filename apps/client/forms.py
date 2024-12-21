from django import forms

from .models import Client, SevenHillsRegistration


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = "__all__"

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        if len(full_name) < 3:
            raise forms.ValidationError("Full name must be at least 3 characters long.")
        return full_name

    def clean(self):
        cleaned_data = super().clean()
        full_name = cleaned_data.get("full_name")

        if len(full_name) < 3:
            self.add_error("full_name", "Full name must be at least 3 characters long.")
            self.fields["full_name"].widget.attrs.update(
                {"class": "form-control is-invalid"}
            )

        return cleaned_data


# Import form
class ImportClientsForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"


class SevenHillsRegistrationForm(forms.ModelForm):
    class Meta:
        model = SevenHillsRegistration
        fields = "__all__"
        widgets = {
            "registration_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "date_of_birth": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telephone_1": forms.TextInput(attrs={"class": "form-control"}),
            "telephone_2": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin_telephone_1": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin_telephone_2": forms.TextInput(attrs={"class": "form-control"}),
            "min_savings_amount": forms.NumberInput(attrs={"class": "form-control"}),
            "saving_goal": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "additional_comments": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        if len(full_name) < 3:
            raise forms.ValidationError("Full name must be at least 3 characters long.")
        return full_name

    def clean(self):
        cleaned_data = super().clean()
        spouse_name = cleaned_data.get("spouse_name")
        marital_status = cleaned_data.get("marital_status")

        if marital_status == "Married" and not spouse_name:
            self.add_error(
                "spouse_name", "Spouse name is required for married individuals."
            )

        return cleaned_data
