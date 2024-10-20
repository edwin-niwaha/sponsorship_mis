from django import forms
from .models import Sale, SaleDetail


# =================================== Sale Form ===================================
class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            "trans_date",
            "customer",
            "sub_total",
            "grand_total",
            "tax_amount",
            "tax_percentage",
            "amount_payed",
            "amount_change",
        ]
        widgets = {
            "trans_date": forms.DateInput(attrs={"type": "date", "required": True}),
            "date_added": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "customer": forms.Select(attrs={"class": "form-control"}),
            "sub_total": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "grand_total": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "tax_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "tax_percentage": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "amount_payed": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "amount_change": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }


# =================================== Sale Detail Form ===================================
class SaleDetailForm(forms.ModelForm):
    class Meta:
        model = SaleDetail
        fields = [
            "sale",
            "product",
            "price",
            "quantity",
            "total_detail",
        ]
        widgets = {
            "sale": forms.Select(attrs={"class": "form-control"}),
            "product": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "total_detail": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }
