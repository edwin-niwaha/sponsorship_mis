from django import forms
from .models import Customer


# =================================== customer form ===================================
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["first_name", "last_name", "address", "email", "phone"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "phone": forms.TextInput(attrs={"placeholder": "Enter your phone number"}),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Enter your email address",
                    "class": "email-input",
                }
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and len(phone) < 10:
            raise forms.ValidationError("Phone number must be at least 10 digits long.")
        return phone
