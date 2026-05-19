from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.http import FileResponse, HttpResponse
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Order, OrderItem
from .utils import assign_manager_to_order
from users.models import User
import os
from datetime import datetime, timedelta
from users.models import User



@login_required
def my_orders(request):
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def manager_dashboard(request):
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    if request.user.role == 'admin':
        orders = Order.objects.all().order_by('-created_at')
    else:
        orders = Order.objects.filter(assigned_manager=request.user).order_by('-created_at')
    
    # Получаем всех менеджеров для передачи заказов
    managers = User.objects.filter(role='manager', is_active=True)
    
    # Получаем всех специалистов для переназначения
    programmers = User.objects.filter(role='programmer', is_active=True)
    marketers = User.objects.filter(role='marketer', is_active=True)
    smms = User.objects.filter(role='smm', is_active=True)
    
    for order in orders:
        from chat.models import ChatMessage
        order.has_unread_messages = ChatMessage.objects.filter(
            order=order, 
            sender__role='client', 
            is_read=False
        ).exists()
    
    return render(request, 'orders/manager_dashboard.html', {
        'orders': orders,
        'managers': managers,
        'programmers': programmers,
        'marketers': marketers,
        'smms': smms,
    })


@login_required
def manager_update_order_status(request, order_id):
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
def manager_chat(request, order_id):
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/manager_chat.html', {'order': order})


@login_required
def manager_analytics(request):
    """Аналитика с вкладками: по компании и по менеджеру"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    # Определяем, какую аналитику показывать
    view_type = request.GET.get('view', 'company')  # company или personal
    
    # Базовый queryset
    if view_type == 'personal':
        orders = Order.objects.filter(assigned_manager=request.user)
        title = "Моя аналитика"
    else:
        orders = Order.objects.all()
        title = "Аналитика компании"
    
    # === ФИЛЬТРЫ ===
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    region = request.GET.get('region')
    if region:
        orders = orders.filter(region=region)
    
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    price_from = request.GET.get('price_from')
    price_to = request.GET.get('price_to')
    if price_from:
        orders = orders.filter(total_price__gte=price_from)
    if price_to:
        orders = orders.filter(total_price__lte=price_to)
    
    # === СОРТИРОВКА ===
    sort_by = request.GET.get('sort', '-created_at')
    orders = orders.order_by(sort_by)
    
    # === СТАТИСТИКА ===
    total_orders = orders.count()
    total_revenue = orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # Статусы
    status_stats = {
        'new': orders.filter(status='new').count(),
        'processing': orders.filter(status='processing').count(),
        'completed': orders.filter(status='completed').count(),
        'cancelled': orders.filter(status='cancelled').count(),
    }
    
            # Динамика по дням (с учётом фильтров)
    orders_by_day = []
    
    # Если выбран период фильтра, показываем график по дням в этом периоде
    if date_from and date_to:
        start = datetime.strptime(date_from, '%Y-%m-%d').date()
        end = datetime.strptime(date_to, '%Y-%m-%d').date()
        delta = (end - start).days + 1
        
        for i in range(delta):
            day = start + timedelta(days=i)
            count = orders.filter(created_at__date=day).count()
            orders_by_day.append({'date': day.strftime('%d.%m'), 'count': count})
    
    # Если фильтр по дате не выбран — показываем последние 30 дней
    else:
        today = timezone.now().date()
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            count = orders.filter(created_at__date=day).count()
            orders_by_day.append({'date': day.strftime('%d.%m'), 'count': count})
    
    # Топ клиентов
    top_clients = orders.filter(status='completed').values('client__username').annotate(
        total_spent=Sum('total_price'),
        orders_count=Count('id')
    ).order_by('-total_spent')[:5]
    
    # Список регионов для фильтра
    regions = Order.objects.exclude(region__isnull=True).exclude(region='').values_list('region', flat=True).distinct()
    
    context = {
        'orders_list': orders,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'status_stats': status_stats,
        'orders_by_day': orders_by_day,
        'top_clients': top_clients,
        'regions': regions,
        'date_from': date_from,
        'date_to': date_to,
        'region_filter': region,
        'status_filter': status,
        'price_from': price_from,
        'price_to': price_to,
        'sort_by': sort_by,
        'view_type': view_type,
        'title': title,
    }
    
    return render(request, 'orders/manager_analytics.html', context)


@login_required
def reassign_order(request, order_id):
    """Передача заказа другому менеджеру"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    order = get_object_or_404(Order, id=order_id)
    
    if request.user.role != 'admin' and order.assigned_manager != request.user:
        return redirect('manager_dashboard')
    
    if request.method == 'POST':
        new_manager_id = request.POST.get('new_manager')
        if new_manager_id:
            new_manager = get_object_or_404(User, id=new_manager_id, role='manager')
            order.assigned_manager = new_manager
            order.save()
            
            from chat.models import ChatMessage
            ChatMessage.objects.create(
                order=order,
                sender=request.user,
                message=f"🔄 Заказ передан менеджеру {new_manager.get_full_name() or new_manager.username}",
                is_read=False
            )
    
    return redirect('manager_dashboard')

@login_required
def reassign_specialist(request, order_id, role):
    """Переназначение специалиста (программист, маркетолог, SMM)"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_specialist_id = request.POST.get('new_specialist')
        if new_specialist_id:
            new_specialist = get_object_or_404(User, id=new_specialist_id)
            
            if role == 'programmer':
                order.assigned_programmer = new_specialist
            elif role == 'marketer':
                order.assigned_marketer = new_specialist
            elif role == 'smm':
                order.assigned_smm = new_specialist
            order.save()
            
            # Уведомление в чат
            from chat.models import ChatMessage
            ChatMessage.objects.create(
                order=order,
                sender=request.user,
                message=f"🔄 Переназначен {role} на {new_specialist.get_full_name() or new_specialist.username}",
                is_read=False
            )
    
    return redirect('manager_dashboard')


@login_required
def download_contract(request, order_id):
    """Скачать готовый договор (DOCX)"""
    file_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'Договор на оказание рекламных услуг.docx')
    
    if not os.path.exists(file_path):
        return HttpResponse("Файл договора не найден", status=404)
    
    return FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@login_required
def popular_services(request):
    """Страница с самыми популярными услугами с фильтром по дате"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    from services.models import Service
    from .models import Order
    from datetime import datetime
    
    # Получаем параметры фильтрации
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Базовый queryset заказов
    orders = Order.objects.all()
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Словарь для сбора статистики
    services_stats = {}
    
    # 1. Считаем услуги из обычных заказов
    for order in orders:
        for item in order.items.all():
            for service in item.package.available_services.all():
                if service.name not in services_stats:
                    services_stats[service.name] = {'count': 0, 'revenue': 0, 'price': service.price}
                services_stats[service.name]['count'] += item.quantity
                services_stats[service.name]['revenue'] += float(service.price) * item.quantity
    
    # 2. Считаем услуги из кастомных заказов
    for order in orders:
        if order.services_data and 'items' in order.services_data:
            for service_item in order.services_data['items']:
                if service_item.get('type') == 'custom':
                    for service in service_item.get('services', []):
                        name = service.get('name')
                        price = service.get('price', 0)
                        if name:
                            if name not in services_stats:
                                services_stats[name] = {'count': 0, 'revenue': 0, 'price': price}
                            services_stats[name]['count'] += 1
                            services_stats[name]['revenue'] += price
    
    # Преобразуем в список и сортируем
    popular_list = []
    for name, data in services_stats.items():
        popular_list.append({
            'name': name,
            'price': data['price'],
            'orders_count': data['count'],
            'total_revenue': data['revenue'],
        })
    
    popular_list.sort(key=lambda x: x['orders_count'], reverse=True)
    top_services = popular_list[:10]
    
    context = {
        'top_services': top_services,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'orders/popular_services.html', context)

@login_required
def manager_rating(request):
    """Рейтинг менеджеров с фильтром по дате"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    from users.models import User
    from django.db.models import Sum, Count
    from datetime import datetime
    
    # Получаем параметры фильтрации
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Базовый queryset заказов
    orders = Order.objects.all()
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Получаем параметр сортировки
    sort_by = request.GET.get('sort', 'total_orders')
    
    managers = User.objects.filter(role='manager', is_active=True)
    manager_stats = []
    
    for manager in managers:
        manager_orders = orders.filter(assigned_manager=manager)
        total_orders = manager_orders.count()
        completed_orders = manager_orders.filter(status='completed').count()
        total_revenue = manager_orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
        avg_check = total_revenue / completed_orders if completed_orders > 0 else 0
        
        manager_stats.append({
            'name': manager.get_full_name() or manager.username,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'total_revenue': total_revenue,
            'avg_check': avg_check,
        })
    
    # Сортировка
    reverse = True
    if sort_by == 'avg_check':
        manager_stats.sort(key=lambda x: x['avg_check'], reverse=reverse)
    elif sort_by == 'total_orders':
        manager_stats.sort(key=lambda x: x['total_orders'], reverse=reverse)
    elif sort_by == 'total_revenue':
        manager_stats.sort(key=lambda x: x['total_revenue'], reverse=reverse)
    elif sort_by == 'completed_orders':
        manager_stats.sort(key=lambda x: x['completed_orders'], reverse=reverse)
    else:
        manager_stats.sort(key=lambda x: x['total_orders'], reverse=reverse)
    
    return render(request, 'orders/manager_rating.html', {
        'managers': manager_stats,
        'sort_by': sort_by,
        'date_from': date_from,
        'date_to': date_to,
    })