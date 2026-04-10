"""StudySync Forms"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile


class RegisterForm(UserCreationForm):
    """FR-01: Registration form with name + email."""
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class SessionStartForm(forms.Form):
    """FR-04: Session start form with optional subject tag."""
    subject = forms.CharField(
        max_length=100,
        required=False,
        initial='General',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject / Topic (optional)',
        })
    )


class ProfileForm(forms.ModelForm):
    """FR-11: Profile settings form for goals and notifications."""
    class Meta:
        model = UserProfile
        fields = ['daily_goal_minutes', 'weekly_goal_minutes', 'sns_notifications_enabled']
        widgets = {
            'daily_goal_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'weekly_goal_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'sns_notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'daily_goal_minutes': 'Daily Goal (minutes)',
            'weekly_goal_minutes': 'Weekly Goal (minutes)',
            'sns_notifications_enabled': 'Enable SNS Push Notifications',
        }
