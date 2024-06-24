from django import forms
from .models import Client

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
            self.fields["full_name"].widget.attrs.update({"class": "form-control is-invalid"})

        return cleaned_data

# Import form
class ImportClientsForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"