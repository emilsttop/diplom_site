from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from users.models import User

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(
    max_length=20, 
    required=True, 
    label='Телефон',
    widget=forms.TextInput(attrs={'placeholder': '+7 (999) 999-99-99'}),
)
    last_name = forms.CharField(max_length=150, required=True, label='Фамилия')
    first_name = forms.CharField(max_length=150, required=True, label='Имя')
    patronymic = forms.CharField(max_length=150, required=False, label='Отчество')

    class Meta:
        model = User
        fields = ['username', 'last_name', 'first_name', 'patronymic', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'client'
        user.phone = self.cleaned_data['phone']
        user.last_name = self.cleaned_data['last_name']
        user.first_name = self.cleaned_data['first_name']
        user.patronymic = self.cleaned_data.get('patronymic', '')
        if commit:
            user.save()
        return user