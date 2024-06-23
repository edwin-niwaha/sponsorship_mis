from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import datetime

from.models import (
    ChildPayments,
)

# =================================== Child Payments Form ===================================
class ChildPaymentForm(forms.ModelForm):
    current_year = datetime.now().year

    payment_year = forms.IntegerField(
        label=_('Year of payment'), 
        widget=forms.NumberInput(attrs={"type": "number", "required": True}),
        min_value=2018,
        max_value=current_year,
    )

    class Meta:
        model = ChildPayments
        exclude = ("sponsor", "child", "is_valid",)

        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "month": forms.Select(attrs={'class': 'form-control', "required": True}),
            "amount": forms.NumberInput(attrs={"type": "number", "required": True}),
        }
        
    def clean_payment_year(self):
        payment_year = self.cleaned_data['payment_year']
        
        # Example custom validation: Ensure payment_year is within a specific range
        if payment_year < 2018 or payment_year > self.current_year:
            raise forms.ValidationError(f"Payment year must be between 2018 and {self.current_year}.")

        # Add more validation as needed
        
        return payment_year

    
# =================================== Child Payment Edit Form ===================================
class ChildPaymentEditForm(forms.ModelForm):
    class Meta:
        model = ChildPayments
        exclude = ("sponsor", "child", "is_valid",)

        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "month": forms.Select(attrs={'class': 'form-control', "required": True}),
            "amount": forms.NumberInput(attrs={"type": "number", "required": True}),
        }