from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('role', 'max_hours')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительно', {'fields': ('role', 'max_hours')}),
    )

# Регистрируем модель User, но не регистрируем Group
admin.site.register(User, CustomUserAdmin)

# Отключаем регистрацию Group
from django.contrib.auth.models import Group
admin.site.unregister(Group)