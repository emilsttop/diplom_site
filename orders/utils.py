from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.http import HttpResponse
from datetime import datetime
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