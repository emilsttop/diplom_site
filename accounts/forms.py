from django import forms
from django.contrib.auth.forms import UserCreationForm
from users.models import User

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True, label='Телефон')

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'client'
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user