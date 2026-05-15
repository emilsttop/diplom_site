from django.db import models
from users.models import User
from services.models import ServicePackage

class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('completed', 'Выполнен'),
        ('cancelled', 'Отменён'),
    )
    
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Клиент')
    packages = models.ManyToManyField('services.ServicePackage', through='OrderItem', verbose_name='Пакеты услуг', related_name='order_items')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Итого')
    services_data = models.JSONField(default=dict, blank=True, verbose_name="Данные услуг (для кастомных)")
    
    # Ответственный менеджер
    assigned_manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_orders',
        verbose_name='Ответственный менеджер',
        limit_choices_to={'role': 'manager'}
    )
    
    def __str__(self):
        return f"Заказ #{self.id} - {self.client.username}"
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    
    def __str__(self):
        return f"{self.package.name} x{self.quantity}"