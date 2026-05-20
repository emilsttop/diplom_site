from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from orders.models import Order
from users.models import User 
from django.db import models
from .models import ChatMessage, SpecialistChatMessage

@login_required
def get_messages(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Проверка доступа
        if request.user.role == 'client' and order.client != request.user:
            return JsonResponse({'messages': [], 'error': 'Нет доступа'}, status=200)
        
        # Получаем все сообщения
        messages = ChatMessage.objects.filter(order=order).order_by('created_at')
        
        # Фильтруем для клиента
        if request.user.role == 'client':
            messages = messages.exclude(message__startswith='🔔 Новый заказ')
            messages = messages.exclude(message__icontains='Переназначен')
        
        # Отмечаем прочитанные
        if request.user.role in ['manager', 'admin']:
            messages.filter(sender__role='client', is_read=False).update(is_read=True)
        else:
            messages.filter(sender__role='manager', is_read=False).update(is_read=True)
        
        # Формируем ответ
        data = []
        for msg in messages:
            data.append({
                'id': msg.id,
                'sender': msg.sender.username,
                'sender_name': f"{msg.sender.last_name} {msg.sender.first_name}".strip() or msg.sender.username,
                'sender_role': msg.sender.role,
                'message': msg.message,
                'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M'),
                'is_read': msg.is_read,
            })
        
        return JsonResponse({'messages': data})
        
    except Exception as e:
        print(f"Ошибка в get_messages: {e}")
        return JsonResponse({'messages': [], 'error': str(e)}, status=200)


@login_required
def send_message(request, order_id):
    """API: отправить сообщение (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешён'}, status=405)
    
    try:
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
            message=message_text,
            is_read=False
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'sender': message.sender.username,
                'sender_name': f"{message.sender.last_name} {message.sender.first_name}".strip() or message.sender.username,
                'sender_role': message.sender.role,
                'message': message.message,
                'created_at': message.created_at.strftime('%d.%m.%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_unread_count(request):
    """API: получить количество непрочитанных сообщений (для клиента, менеджера, специалиста)"""
    try:
        if request.user.role == 'client':
            # Клиент считает непрочитанные сообщения от менеджеров
            orders = Order.objects.filter(client=request.user)
            unread = ChatMessage.objects.filter(
                order__in=orders, 
                sender__role='manager', 
                is_read=False
            ).count()
        elif request.user.role in ['manager', 'admin']:
            # Менеджер считает непрочитанные сообщения от клиентов
            unread = ChatMessage.objects.filter(
                sender__role='client', 
                is_read=False
            ).count()
        elif request.user.role in ['programmer', 'marketer', 'smm']:
            # Специалист считает непрочитанные сообщения от менеджера
            unread = SpecialistChatMessage.objects.filter(
                receiver=request.user, 
                is_read=False
            ).count()
        else:
            unread = 0
        
        return JsonResponse({'unread_count': unread})
    except Exception as e:
        print(f"Ошибка в get_unread_count: {e}")
        return JsonResponse({'unread_count': 0, 'error': str(e)}, status=200)


@login_required
def get_manager_specialist_unread_count(request):
    """API: получить количество непрочитанных сообщений от специалистов для менеджера"""
    try:
        if request.user.role not in ['manager', 'admin']:
            return JsonResponse({'unread_count': 0, 'error': 'Нет доступа'}, status=200)
        
        unread = SpecialistChatMessage.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({'unread_count': unread})
    except Exception as e:
        print(f"Ошибка в get_manager_specialist_unread_count: {e}")
        return JsonResponse({'unread_count': 0, 'error': str(e)}, status=200)


@login_required
def get_specialist_messages(request, order_id, specialist_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        specialist = get_object_or_404(User, id=specialist_id)
        
        # Проверка доступа
        if request.user.role == 'specialist' and request.user != specialist:
            return JsonResponse({'messages': [], 'error': 'Нет доступа'}, status=200)
        if request.user.role == 'manager' and order.assigned_manager != request.user:
            return JsonResponse({'messages': [], 'error': 'Нет доступа'}, status=200)
        
        # Получаем сообщения между менеджером и специалистом
        messages = SpecialistChatMessage.objects.filter(
            order=order
        ).filter(
            (models.Q(sender=specialist) & models.Q(receiver=order.assigned_manager)) |
            (models.Q(sender=order.assigned_manager) & models.Q(receiver=specialist))
        ).order_by('created_at')
        
        # Помечаем все сообщения, где текущий пользователь является получателем
        messages.filter(receiver=request.user, is_read=False).update(is_read=True)
        
        data = []
        for msg in messages:
            data.append({
                'id': msg.id,
                'sender': msg.sender.username,
                'sender_name': f"{msg.sender.last_name} {msg.sender.first_name}".strip() or msg.sender.username,
                'sender_role': msg.sender.role,
                'message': msg.message,
                'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M'),
                'is_read': msg.is_read,
            })
        
        return JsonResponse({'messages': data})
    except Exception as e:
        print(f"Ошибка в get_specialist_messages: {e}")
        return JsonResponse({'messages': [], 'error': str(e)}, status=200)


@login_required
def send_specialist_message(request, order_id, specialist_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешён'}, status=405)
    
    try:
        order = get_object_or_404(Order, id=order_id)
        specialist = get_object_or_404(User, id=specialist_id)
        
        # Проверка доступа
        if request.user.role == 'specialist' and request.user != specialist:
            return JsonResponse({'error': 'Нет доступа'}, status=403)
        if request.user.role == 'manager' and order.assigned_manager != request.user:
            return JsonResponse({'error': 'Нет доступа'}, status=403)
        
        message_text = request.POST.get('message', '').strip()
        if not message_text:
            return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)
        
        # Определяем получателя
        if request.user.role == 'manager':
            receiver = specialist
        else:
            receiver = order.assigned_manager
        
        message = SpecialistChatMessage.objects.create(
            order=order,
            sender=request.user,
            receiver=receiver,
            message=message_text,
            is_read=False
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'sender': message.sender.username,
                'sender_name': f"{message.sender.last_name} {message.sender.first_name}".strip() or message.sender.username,
                'sender_role': message.sender.role,
                'message': message.message,
                'created_at': message.created_at.strftime('%d.%m.%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def specialist_chat_page(request, order_id, specialist_id):
    order = get_object_or_404(Order, id=order_id)
    specialist = get_object_or_404(User, id=specialist_id)
    if request.user != specialist:
        return redirect('catalog')
    return render(request, 'chat/specialist_chat.html', {'order': order, 'specialist': specialist})


@login_required
def manager_specialist_chat_page(request, order_id, specialist_id):
    order = get_object_or_404(Order, id=order_id)
    specialist = get_object_or_404(User, id=specialist_id)
    if request.user.role not in ['manager', 'admin'] or order.assigned_manager != request.user:
        return redirect('catalog')
    return render(request, 'chat/manager_specialist_chat.html', {'order': order, 'specialist': specialist})


@login_required
def get_specialist_unread_status(request, order_id, specialist_id):
    """Проверяет, есть ли непрочитанные сообщения у специалиста по конкретному заказу"""
    try:
        order = get_object_or_404(Order, id=order_id)
        specialist = get_object_or_404(User, id=specialist_id)
        
        # Проверка доступа
        if request.user != specialist:
            return JsonResponse({'has_unread': False, 'error': 'Нет доступа'}, status=200)
        
        has_unread = SpecialistChatMessage.objects.filter(
            order_id=order_id,
            receiver=specialist,
            is_read=False
        ).exists()
        
        return JsonResponse({'has_unread': has_unread})
    except Exception as e:
        print(f"Ошибка в get_specialist_unread_status: {e}")
        return JsonResponse({'has_unread': False, 'error': str(e)}, status=200)