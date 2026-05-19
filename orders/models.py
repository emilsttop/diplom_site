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
    created_at = models.DateTimeField(verbose_name='Дата создания')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Итого')
    services_data = models.JSONField(default=dict, blank=True, verbose_name="Данные услуг (для кастомных)")
    region = models.CharField(max_length=100, blank=True, null=True, verbose_name="Регион")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий к заказу")
        # Назначенные специалисты
    assigned_programmer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programmer_tasks', limit_choices_to={'role': 'programmer'},
        verbose_name='Программист'
    )
    assigned_marketer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='marketer_tasks', limit_choices_to={'role': 'marketer'},
        verbose_name='Маркетолог'
    )
    assigned_smm = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='smm_tasks', limit_choices_to={'role': 'smm'},
        verbose_name='SMM-менеджер'
    )
    
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
        # Загрузка специалистов в часах
    programmer_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Часы программиста")
    marketer_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Часы маркетолога")
    smm_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Часы SMM")
    
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