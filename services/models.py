from django.db import models

class ServicePackage(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название пакета")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    services_list = models.TextField(verbose_name="Входящие услуги", help_text="Перечислите через запятую")
    
    def __str__(self):
        return self.name