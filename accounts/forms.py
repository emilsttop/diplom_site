from django import forms
from django.contrib.auth.forms import UserCreationForm
from users.models import User

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'client'  # Новые пользователи — сразу клиенты
        if commit:
            user.save()
        return user