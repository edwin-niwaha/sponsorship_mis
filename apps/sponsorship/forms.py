from django import forms
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from .models import ChildSponsorship, StaffSponsorship


# =================================== Base Sponsorship Form ===================================
class BaseSponsorshipEditForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        sponsor = cleaned_data.get("sponsor")
        start_date = cleaned_data.get("start_date")
        sponsorship_type = cleaned_data.get("sponsorship_type")

        # Check if a sponsorship with the same sponsor, start_date, and sponsorship_type already exists
        existing_sponsorship = self.Meta.model.objects.filter(
            sponsor=sponsor, start_date=start_date, sponsorship_type=sponsorship_type
        ).exclude(
            id=self.instance.id if self.instance else None
        )  # Exclude the current instance if editing

        if existing_sponsorship.exists():
            raise ValidationError("A sponsorship with the same details already exists.")

        return cleaned_data


# =================================== Child Sponsorship Form ===================================
class ChildSponsorshipForm(forms.ModelForm):
    class Meta:
        model = ChildSponsorship
        exclude = ("sponsor", "child", "is_active", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "sponsorship_type": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
        }


# =================================== Child Sponsorship Edit Form ===================================
class ChildSponsorshipEditForm(BaseSponsorshipEditForm):
    class Meta:
        model = ChildSponsorship
        fields = ("child", "sponsor", "start_date", "sponsorship_type")

        widgets = {
            "child": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "sponsor": forms.Select(attrs={"class": "form-control", "required": True}),
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "sponsorship_type": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
        }


# =================================== Staff Sponsorship Form ===================================
class StaffSponsorshipForm(forms.ModelForm):
    class Meta:
        model = StaffSponsorship
        exclude = ("sponsor", "staff", "is_active", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "sponsorship_type": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),  #
        }


# =================================== Staff Sponsorship Edit Form ===================================
class StaffSponsorshipEditForm(BaseSponsorshipEditForm):
    class Meta:
        model = StaffSponsorship
        fields = ("staff", "sponsor", "start_date", "sponsorship_type")

        widgets = {
            "staff": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "sponsor": forms.Select(attrs={"class": "form-control", "required": True}),
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "sponsorship_type": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
        }


# =================================== Payment Form for Flutterwave ===================================
# class DonationForm(forms.Form):
#     name = forms.CharField(max_length=200, required=True)
#     email = forms.EmailField(required=True)
#     phone_number = forms.CharField(max_length=15, required=True)
#     amount = forms.DecimalField(min_value=1.00, decimal_places=2, required=True)



class DonationForm(forms.Form):
    name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Your full name"
        })
    )
    phone_number = PhoneNumberField(
        region="UG",  # set default region, e.g., Uganda
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+256..."
        })
    )
    amount = forms.DecimalField(
        min_value=1.00,
        max_digits=10,      # up to 9,999,999.99
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter amount"
        })
    )

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount < 1:
            raise forms.ValidationError("Minimum donation is 1 unit.")
        return amount
