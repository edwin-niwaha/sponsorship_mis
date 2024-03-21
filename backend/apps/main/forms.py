from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from .models import *


class UploadForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs['class'] = 'form-control-file'


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = "__all__"
        widgets={'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
                 'siblings': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'background_info': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'responsibility': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'mother_description': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'staff_comment': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'father_description': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                 'c_interest': forms.Textarea(attrs={'class': "form-control", "rows":3}),
                 }
        
    #Form validation
    def clean(self):
        super(ChildForm, self).clean()

        full_name = self.cleaned_data.get('full_name')
        preferred_name = self.cleaned_data.get('preferred_name')

        if len(full_name)<3:
            self.add_error('full_name','Can not save first name less than 3 characters long')
            self.fields['full_name'].widget.attrs.update({'class': 'form-control  is-invalid'})

        if len(preferred_name)<3:
            self.add_error('preferred_name','Can not save last name less than 3 characters long')
            self.fields['preferred_name'].widget.attrs.update({'class': 'form-control  is-invalid'})

        return self.cleaned_data
    

class ChildProfilePictureForm(forms.ModelForm):
    class Meta:
        model = ChildProfilePicture
        fields = ['picture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['picture'].widget = forms.FileInput(attrs={'accept': 'image/*'})

    def clean_picture(self):
        picture = self.cleaned_data.get('picture')
        return picture