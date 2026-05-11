from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Order
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from django.utils import timezone
from chat.models import ChatMessage  

@login_required
def my_orders(request):
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})

@login_required
def manager_dashboard(request):
    """Панель менеджера - все заказы (только для менеджеров и админов)"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    orders = Order.objects.all().order_by('-created_at')
    
    # Для каждого заказа добавляем флаг: есть ли непрочитанные сообщения от клиента
    for order in orders:
        order.has_unread_messages = ChatMessage.objects.filter(
            order=order, 
            sender__role='client', 
            is_read=False
        ).exists()
    
    return render(request, 'orders/manager_dashboard.html', {'orders': orders})

@login_required
def manager_update_order_status(request, order_id):
    """Менеджер меняет статус заказа"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
    return redirect('manager_dashboard')

@login_required
def manager_send_message(request, order_id):
    """Менеджер отправляет сообщение клиенту"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            # TODO: создать модель сообщения
            # Пока просто заглушка
            pass
    return redirect('manager_dashboard')

@login_required
def manager_analytics(request):
    """Аналитика для менеджера: графики, отчёты, задолженности"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    # Получаем все заказы
    all_orders = Order.objects.all()
    
    # 1. Статистика по статусам
    status_stats = {
        'new': all_orders.filter(status='new').count(),
        'processing': all_orders.filter(status='processing').count(),
        'completed': all_orders.filter(status='completed').count(),
        'cancelled': all_orders.filter(status='cancelled').count(),
    }
    
    # 2. Динамика заказов по дням (последние 7 дней)
    today = timezone.now().date()
    orders_by_day = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = all_orders.filter(created_at__range=(day_start, day_end)).count()
        total = all_orders.filter(created_at__range=(day_start, day_end)).aggregate(Sum('total_price'))['total_price__sum'] or 0
        orders_by_day.append({
            'date': day.strftime('%d.%m'),
            'count': count,
            'total': float(total)
        })
    
    # 3. Задолженности (заказы в работе, но не завершённые)
    # Для демо считаем заказы в статусе 'processing' как "с задолженностью"
    debts = all_orders.filter(status='processing').select_related('client')
    debt_total = debts.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # 4. Топ-5 клиентов по сумме заказов
    top_clients = all_orders.filter(status='completed').values('client__username').annotate(
        total_spent=Sum('total_price'),
        orders_count=Count('id')
    ).order_by('-total_spent')[:5]
    
    # 5. Самые популярные услуги
    from services.models import ServicePackage
    popular_services = []
    for package in ServicePackage.objects.all():
        order_count = all_orders.filter(items__package=package).count()
        popular_services.append({
            'name': package.name,
            'orders_count': order_count,
            'revenue': all_orders.filter(items__package=package, status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
        })
    popular_services = sorted(popular_services, key=lambda x: x['orders_count'], reverse=True)[:5]
    
    context = {
        'status_stats': status_stats,
        'orders_by_day': orders_by_day,
        'debts': debts,
        'debt_total': debt_total,
        'top_clients': top_clients,
        'popular_services': popular_services,
        'total_orders': all_orders.count(),
        'total_revenue': all_orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0,
    }
    
    return render(request, 'orders/manager_analytics.html', context)

@login_required
def manager_chat(request, order_id):
    """Отдельная страница чата для менеджера"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/manager_chat.html', {'order': order})