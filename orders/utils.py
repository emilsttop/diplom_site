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

def generate_contract(order):
    """Генерация PDF-договора для заказа с поддержкой русского языка"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="dogovor_{order.id}.pdf"'
    
    # Регистрируем шрифт с поддержкой кириллицы
    # Пробуем разные стандартные пути к шрифтам Windows
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/ariali.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    
    font_registered = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('RussianFont', font_path))
            font_registered = True
            break
    
    if not font_registered:
        # Если шрифт не найден, используем стандартный (английский)
        pdfmetrics.registerFont(TTFont('RussianFont', 'C:/Windows/Fonts/arial.ttf'))
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # Используем русский шрифт
    p.setFont("RussianFont", 16)
    p.drawString(50, height - 50, "ДОГОВОР №" + str(order.id))
    
    p.setFont("RussianFont", 12)
    p.drawString(50, height - 80, f"г. Москва                                    {datetime.now().strftime('%d.%m.%Y')}")
    
    # Тело договора
    y = height - 120
    p.setFont("RussianFont", 12)
    p.drawString(50, y, "1. ПРЕДМЕТ ДОГОВОРА")
    y -= 25
    p.setFont("RussianFont", 10)
    p.drawString(50, y, "Исполнитель обязуется оказать услуги по продвижению, а Заказчик обязуется оплатить их.")
    
    y -= 20
    p.drawString(50, y, "Состав услуг:")
    y -= 15
    
    for item in order.items.all():
        text = f"- {item.package.name} x{item.quantity} = {item.price * item.quantity} ₽"
        p.drawString(60, y, text)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("RussianFont", 10)
    
    y -= 15
    p.setFont("RussianFont", 12)
    p.drawString(50, y, f"ИТОГО: {order.total_price} ₽")
    
    # Подписи
    y -= 50
    p.setFont("RussianFont", 10)
    p.drawString(50, y, "ИСПОЛНИТЕЛЬ:")
    p.drawString(300, y, "ЗАКАЗЧИК:")
    y -= 15
    p.drawString(50, y, "_____________ /________ /")
    p.drawString(300, y, f"_____________ /{order.client.username} /")
    
    p.showPage()
    p.save()
    
    return response
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
    specialists = User.objects.filter(role=role, is_active=True)
    if not specialists:
        return False
    
    for specialist in specialists:
        # Текущая загрузка (активные заказы)
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
        
        if current_load + required_hours <= specialist.max_hours:
            return True
    return False