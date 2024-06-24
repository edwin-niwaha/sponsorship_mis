from django import forms

from .models import Staff, StaffDeparture

# =================================== STAFF FORM ===================================

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        exclude = ("is_departed", "is_sponsored" )
        widgets = {
            "date_started_work": forms.DateInput(attrs={"type": "date", "required": True}),
            "gender": forms.Select(attrs={'class': 'form-control', "required": True}),
            "marital_status": forms.Select(attrs={'class': 'form-control', "required": True}),
            "department": forms.Select(attrs={'class': 'form-control', "required": True}),
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
    
# =================================== STAFF DEPATURE ===================================
class StaffDepartureForm(forms.ModelForm):
    class Meta:
        model = StaffDeparture
        exclude = ("staff", )
        widgets ={
            "departure_date": forms.DateInput(attrs={"type": "date"}),
            "departure_reason": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }