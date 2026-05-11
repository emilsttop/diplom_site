from .models import ChatMessage
from orders.models import Order

def unread_messages_count(request):
    if request.user.is_authenticated:
        if request.user.role in ['manager', 'admin']:
            # Считаем непрочитанные сообщения (включая уведомления о новых заказах)
            count = ChatMessage.objects.filter(
                sender__role='client', 
                is_read=False,
                order__assigned_manager=request.user  # только заказы этого менеджера
            ).count()
            # Также считаем заказы без назначенного менеджера (общие)
            count += ChatMessage.objects.filter(
                sender__role='client', 
                is_read=False,
                order__assigned_manager__isnull=True
            ).count()
        elif request.user.role == 'client':
            orders = Order.objects.filter(client=request.user)
            count = ChatMessage.objects.filter(order__in=orders, sender__role='manager', is_read=False).count()
        else:
            count = 0
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}