from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from orders.models import Order
from .models import ChatMessage

@login_required
def get_messages(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.user.role == 'client' and order.client != request.user:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    messages = ChatMessage.objects.filter(order=order)
    
    # ⬇️ ДОБАВЬ ЭТОТ ФИЛЬТР ⬇️
    # Клиент не должен видеть технические сообщения
    if request.user.role == 'client':
        messages = messages.exclude(message__startswith='🔔 Новый заказ')
    
    # Отмечаем сообщения как прочитанные
    if request.user.role in ['manager', 'admin']:
        messages.filter(sender__role='client', is_read=False).update(is_read=True)
    else:
        messages.filter(sender__role='manager', is_read=False).update(is_read=True)
    
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_role': msg.sender.role,
            'message': msg.message,
            'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M'),
            'is_read': msg.is_read,
        })
    
    return JsonResponse({'messages': data})

@login_required
def send_message(request, order_id):
    """API: отправить сообщение (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешён'}, status=405)
    
    order = get_object_or_404(Order, id=order_id)
    
    # Проверка прав
    if request.user.role == 'client' and order.client != request.user:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    message_text = request.POST.get('message', '').strip()
    if not message_text:
        return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)
    
    message = ChatMessage.objects.create(
        order=order,
        sender=request.user,
        message=message_text
    )
    
    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'sender': message.sender.username,
            'sender_role': message.sender.role,
            'message': message.message,
            'created_at': message.created_at.strftime('%d.%m.%Y %H:%M'),
        }
    })

@login_required
def get_unread_count(request):
    """API: получить количество непрочитанных сообщений"""
    if request.user.role == 'client':
        # Клиент считает сообщения от менеджеров по своим заказам
        orders = Order.objects.filter(client=request.user)
        unread = ChatMessage.objects.filter(order__in=orders, sender__role='manager', is_read=False).count()
    else:
        # Менеджер/админ считает сообщения от клиентов
        unread = ChatMessage.objects.filter(sender__role='client', is_read=False).count()
    
    return JsonResponse({'unread_count': unread})