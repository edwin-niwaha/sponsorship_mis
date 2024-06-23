from django import forms
from django.core.exceptions import ValidationError

from .models import ChildSponsorship, Sponsor, SponsorDeparture, StaffSponsorship

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
            ),

            "gender": forms.Select(attrs={'class': 'form-control', "required": True}),
            "sponsorship_type_at_signup": forms.Select(attrs={'class': 'form-control', "required": True}),
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
        widgets ={
             "departure_date": forms.DateInput(attrs={"type": "date"}),
            "departure_reason": forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

# =================================== Base Sponsorship Form ===================================
class BaseSponsorshipEditForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        sponsor = cleaned_data.get('sponsor')
        start_date = cleaned_data.get('start_date')
        sponsorship_type = cleaned_data.get('sponsorship_type')

        # Check if a sponsorship with the same sponsor, start_date, and sponsorship_type already exists
        existing_sponsorship = self.Meta.model.objects.filter(
            sponsor=sponsor,
            start_date=start_date,
            sponsorship_type=sponsorship_type
        ).exclude(id=self.instance.id if self.instance else None)  # Exclude the current instance if editing

        if existing_sponsorship.exists():
            raise ValidationError('A sponsorship with the same details already exists.')

        return cleaned_data

# =================================== Child Sponsorship Form ===================================
class ChildSponsorshipForm(forms.ModelForm):
    class Meta:
        model = ChildSponsorship
        exclude = ("sponsor", "child", "is_active", "end_date")
        widgets ={
             "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
             "sponsorship_type": forms.Select(attrs={'class': 'form-control', "required": True}),
        }

# =================================== Child Sponsorship Edit Form ===================================
class ChildSponsorshipEditForm(BaseSponsorshipEditForm):
    class Meta:
        model = ChildSponsorship
        fields = ('child', 'sponsor', 'start_date', 'sponsorship_type')

        widgets = {
            "child": forms.Select(attrs={'class': 'form-control',}),
            "sponsor": forms.Select(attrs={'class': 'form-control', "required": True}), 
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "sponsorship_type": forms.Select(attrs={'class': 'form-control', "required": True}),
        }
        
# =================================== Staff Sponsorship Form ===================================

class StaffSponsorshipForm(forms.ModelForm):
    class Meta:
        model = StaffSponsorship
        exclude = ("sponsor", "staff", "is_active", "end_date")
        widgets ={
             "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
             "sponsorship_type": forms.Select(attrs={'class': 'form-control', "required": True}),  #
        }


class StaffSponsorshipEditForm(BaseSponsorshipEditForm):
    class Meta:
        model = StaffSponsorship
        fields = ('staff', 'sponsor', 'start_date', 'sponsorship_type')

        widgets = {
            "staff": forms.Select(attrs={'class': 'form-control',}),
            "sponsor": forms.Select(attrs={'class': 'form-control', "required": True}), 
            "start_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "sponsorship_type": forms.Select(attrs={'class': 'form-control', "required": True}),
        }
