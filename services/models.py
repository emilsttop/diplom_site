from django.db import models

class ServicePackage(models.Model):
    """Пакет услуг (12 штук)"""
    name = models.CharField(max_length=200, verbose_name="Название пакета")
    description = models.TextField(verbose_name="Описание")
    icon = models.CharField(max_length=10, default="📦", verbose_name="Иконка")
    
    # Услуги, которые можно выбрать в этом пакете
    available_services = models.ManyToManyField('Service', verbose_name="Доступные услуги на выбор")
    
    min_services = models.PositiveIntegerField(default=5, verbose_name="Минимальное количество услуг")
    max_services = models.PositiveIntegerField(default=10, verbose_name="Максимальное количество услуг")
    
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    sort_order = models.IntegerField(default=0, verbose_name="Порядок")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['sort_order']
        verbose_name = "Пакет услуг"
        verbose_name_plural = "Пакеты услуг"

class Service(models.Model):
    """Отдельная услуга"""
    name = models.CharField(max_length=200, verbose_name="Название услуги")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    
    def __str__(self):
        return f"{self.name} - {self.price} ₽"
    
    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"