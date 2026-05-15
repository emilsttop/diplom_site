from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
    ('admin', 'Администратор'),
    ('manager', 'Менеджер'),
    ('client', 'Клиент'),
    ('programmer', 'Программист'),
    ('marketer', 'Маркетолог'),
    ('smm', 'SMM-менеджер'),
)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"