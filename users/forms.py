from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, UserProfile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.RadioSelect,
        label='I am a',
        help_text='Select your role to get started'
    )
    agree_terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms of Service and Privacy Policy'
    )

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2', 'role', 'agree_terms')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with that email already exists.')
        return email

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'location', 'website', 'linkedin_url', 'github_url',
                 'email_notifications', 'marketing_emails')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'avatar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        self.fields['avatar'].required = False