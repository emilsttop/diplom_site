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
    # Добавляем связь с новой таблицей Role
    role_link = models.ForeignKey(
        'Role', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Роль (новая система)"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Role(models.Model):
    """Таблица ролей с возможностью связи с пользователями"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Название роли")
    code = models.CharField(max_length=20, unique=True, verbose_name="Код роли")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ['name']

    def __str__(self):
        return self.name