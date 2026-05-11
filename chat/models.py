from django.db import models
from users.models import User
from orders.models import Order

class ChatMessage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='messages', verbose_name='Заказ')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    message = models.TextField(verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    
    def __str__(self):
        return f"Сообщение к заказу #{self.order.id} от {self.sender.username}"
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'