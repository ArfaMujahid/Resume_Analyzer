from django import forms
from .models import ResumeDocument


class ResumeUploadForm(forms.ModelForm):
    file = forms.FileField(
        label='Select Resume',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.txt'
        }),
        help_text='Supported formats: PDF, DOC, DOCX, TXT (Max 20MB)'
    )

    class Meta:
        model = ResumeDocument
        fields = []  # We'll handle file upload manually

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError('Please select a file to upload.')

        # Check file extension
        valid_extensions = ['.pdf', '.doc', '.docx', '.txt']
        file_extension = '.' + file.name.split('.')[-1].lower()

        if file_extension not in valid_extensions:
            raise forms.ValidationError(
                f'Unsupported file type. Please upload one of: {", ".join(valid_extensions)}'
            )

        # Check file size (20MB max)
        if file.size > 20 * 1024 * 1024:
            raise forms.ValidationError('File size must be less than 20MB.')

        return file