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
    max_hours = models.PositiveIntegerField(default=45, verbose_name="Максимальная загрузка (часы)")
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True, null=True)
    # Добавляем новые поля
    last_name = models.CharField(max_length=150, verbose_name="Фамилия", blank=False, null=False)
    first_name = models.CharField(max_length=150, verbose_name="Имя", blank=False, null=False)
    patronymic = models.CharField(max_length=150, verbose_name="Отчество", blank=True, null=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.get_role_display()})"