from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.http import HttpResponse
from datetime import datetime
from users.models import User
from django.db.models import Sum
import os
from users.models import User
from .models import Order
from chat.models import ChatMessage
def assign_manager_to_order(order):
    """Автоматически назначает менеджера с наименьшим количеством активных заказов"""
    managers = User.objects.filter(role='manager', is_active=True)
    
    if not managers:
        return None
    
    # Считаем количество активных заказов (не завершённых) у каждого менеджера
    manager_load = []
    for manager in managers:
        active_orders_count = Order.objects.filter(
            assigned_manager=manager
        ).exclude(status='completed').exclude(status='cancelled').count()
        manager_load.append((manager, active_orders_count))
    
    # Сортируем по загрузке и выбираем самого свободного
    manager_load.sort(key=lambda x: x[1])
    assigned_manager = manager_load[0][0]
    
    # Назначаем менеджера заказу
    order.assigned_manager = assigned_manager
    order.save()
    
    # ✅ Убираем сообщение в чат
    # Сообщение больше не создаётся, чтобы клиент его не видел
    
    return assigned_manager

def get_manager_name(manager):
    """Возвращает имя менеджера или username"""
    if manager:
        return manager.get_full_name() or manager.username
    return "Не назначен"

def assign_specialist(role, new_hours, current_order_id=None):
    """Назначает специалиста с наименьшей текущей загрузкой (без учёта выполненных заказов)"""
    if new_hours == 0:
        return None
    
    specialists = User.objects.filter(role=role, is_active=True)
    if not specialists:
        return None
    
    specialist_load = []
    for specialist in specialists:
        # Исключаем выполненные заказы и текущий заказ
        if role == 'programmer':
            total = Order.objects.filter(
                assigned_programmer=specialist
            ).exclude(status='completed').exclude(id=current_order_id).aggregate(
                total=Sum('programmer_hours')
            )['total'] or 0
        elif role == 'marketer':
            total = Order.objects.filter(
                assigned_marketer=specialist
            ).exclude(status='completed').exclude(id=current_order_id).aggregate(
                total=Sum('marketer_hours')
            )['total'] or 0
        else:  # smm
            total = Order.objects.filter(
                assigned_smm=specialist
            ).exclude(status='completed').exclude(id=current_order_id).aggregate(
                total=Sum('smm_hours')
            )['total'] or 0
        
        specialist_load.append((specialist, total))
        print(f"Специалист {specialist.username}: загрузка {total} ч")
    
    specialist_load.sort(key=lambda x: x[1])
    best = specialist_load[0][0]
    print(f"✅ Выбран {best.username} с загрузкой {specialist_load[0][1]} ч")
    return best

def is_specialist_available(role, required_hours):
    """Проверяет, есть ли свободный специалист для выполнения заказа"""
    try:
        required_hours = float(required_hours)
    except (TypeError, ValueError):
        return False
    
    specialists = User.objects.filter(role=role, is_active=True)
    if not specialists:
        return False
    
    for specialist in specialists:
        if role == 'programmer':
            current_load = Order.objects.filter(
                assigned_programmer=specialist
            ).exclude(status='completed').aggregate(
                total=Sum('programmer_hours')
            )['total'] or 0
        elif role == 'marketer':
            current_load = Order.objects.filter(
                assigned_marketer=specialist
            ).exclude(status='completed').aggregate(
                total=Sum('marketer_hours')
            )['total'] or 0
        else:
            current_load = Order.objects.filter(
                assigned_smm=specialist
            ).exclude(status='completed').aggregate(
                total=Sum('smm_hours')
            )['total'] or 0
        
        # Приводим всё к float
        current_load = float(current_load)
        max_load = float(specialist.max_hours)
        
        if current_load + required_hours <= max_load:
            return True
    return False