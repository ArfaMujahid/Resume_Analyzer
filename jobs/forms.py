from django import forms
from .models import JobDescription


class JobDescriptionForm(forms.ModelForm):
    class Meta:
        model = JobDescription
        fields = ['title', 'company', 'location', 'salary_range', 'min_years_experience', 'degree_requirements']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_range': forms.TextInput(attrs={'class': 'form-control'}),
            'min_years_experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'degree_requirements': forms.TextInput(attrs={'class': 'form-control'}),
        }

    raw_text = forms.CharField(
        label='Job Description',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Paste or type the complete job description here...'
        }),
        help_text='Include responsibilities, requirements, skills, and qualifications'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raw_text'].required = True