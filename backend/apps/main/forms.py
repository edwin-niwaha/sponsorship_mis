from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from .models import *


# custom widget to display "Yes/No" options in the form.
YES_NO_CHOICES = (
    (True, 'Yes'),
    (False, 'No'),
)

class ChildDetailsForm(forms.ModelForm):
    class Meta:

        model = ChildProfile
        fields = "__all__"
        widgets={'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
                 'siblings': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'background_info': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'responsibility': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'mother_description': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'staff_comment': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'father_description': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 }

    #validation
    def clean(self):
        super(ChildDetailsForm, self).clean()

        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')

        if len(first_name)<3:
            self.add_error('first_name','Can not save first name less than 3 characters long')
            self.fields['first_name'].widget.attrs.update({'class': 'form-control  is-invalid'})

        if len(last_name)<3:
            self.add_error('last_name','Can not save last name less than 3 characters long')
            self.fields['last_name'].widget.attrs.update({'class': 'form-control  is-invalid'})

        return self.cleaned_data
    


