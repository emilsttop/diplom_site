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
    
    managers = User.objects.filter(role='manager', is_active=True)
    programmers = User.objects.filter(role='programmer', is_active=True)
    marketers = User.objects.filter(role='marketer', is_active=True)
    smms = User.objects.filter(role='smm', is_active=True)
    
    from django.db.models import Sum
    
    for order in orders:
        from chat.models import ChatMessage
        order.has_unread_messages = ChatMessage.objects.filter(
            order=order, 
            sender__role='client', 
            is_read=False
        ).exists()
        
        # Инициализация переменных перегрузки (на случай, если специалист не назначен)
        order.programmer_overload = False
        order.marketer_overload = False
        order.smm_overload = False
        
        # Общая нагрузка программиста
        if order.assigned_programmer:
            total = Order.objects.filter(
                assigned_programmer=order.assigned_programmer
            ).exclude(status='completed').exclude(status='cancelled').aggregate(
                total=Sum('programmer_hours')
            )['total'] or 0
            order.programmer_overload = total > 45
        
        # Общая нагрузка маркетолога
        if order.assigned_marketer:
            total = Order.objects.filter(
                assigned_marketer=order.assigned_marketer
            ).exclude(status='completed').exclude(status='cancelled').aggregate(
                total=Sum('marketer_hours')
            )['total'] or 0
            order.marketer_overload = total > 45
        
        # Общая нагрузка SMM
        if order.assigned_smm:
            total = Order.objects.filter(
                assigned_smm=order.assigned_smm
            ).exclude(status='completed').exclude(status='cancelled').aggregate(
                total=Sum('smm_hours')
            )['total'] or 0
            order.smm_overload = total > 45
    
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
    """Аналитика с вкладками: Заказы, Специалисты, Услуги"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')

    # --- 1. Данные для вкладки "Заказы" (существующая логика) ---
    view_type = request.GET.get('view', 'company')
    if view_type == 'personal':
        orders = Order.objects.filter(assigned_manager=request.user)
        title = "Моя аналитика"
    else:
        orders = Order.objects.all()
        title = "Аналитика компании"

    # Фильтры для заказов
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

    sort_by = request.GET.get('sort', '-created_at')
    orders = orders.order_by(sort_by)

    # Статистика для вкладки "Заказы"
    total_orders = orders.count()
    total_revenue = orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
    status_stats = {
        'new': orders.filter(status='new').count(),
        'processing': orders.filter(status='processing').count(),
        'completed': orders.filter(status='completed').count(),
        'cancelled': orders.filter(status='cancelled').count(),
    }

    # Динамика по дням
    orders_by_day = []
    if date_from and date_to:
        start = datetime.strptime(date_from, '%Y-%m-%d').date()
        end = datetime.strptime(date_to, '%Y-%m-%d').date()
        delta = (end - start).days + 1
        for i in range(delta):
            day = start + timedelta(days=i)
            count = orders.filter(created_at__date=day).count()
            orders_by_day.append({'date': day.strftime('%d.%m'), 'count': count})
    else:
        today = timezone.now().date()
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            count = orders.filter(created_at__date=day).count()
            orders_by_day.append({'date': day.strftime('%d.%m'), 'count': count})

    top_clients = orders.filter(status='completed').values('client__username').annotate(
        total_spent=Sum('total_price'),
        orders_count=Count('id')
    ).order_by('-total_spent')[:5]

    regions = Order.objects.exclude(region__isnull=True).exclude(region='').values_list('region', flat=True).distinct()

    # --- 2. Данные для вкладки "Специалисты" (из specialists_rating) ---
    role_filter = request.GET.get('role', '')
    date_from_spec = request.GET.get('date_from_spec')
    date_to_spec = request.GET.get('date_to_spec')
    sort_spec = request.GET.get('sort_spec', '-total_orders')
    
    orders_for_spec = Order.objects.all()
    if date_from_spec:
        orders_for_spec = orders_for_spec.filter(created_at__date__gte=date_from_spec)
    if date_to_spec:
        orders_for_spec = orders_for_spec.filter(created_at__date__lte=date_to_spec)

    if role_filter:
        specialists = User.objects.filter(role=role_filter, is_active=True)
    else:
        specialists = User.objects.filter(role__in=['programmer', 'marketer', 'smm'], is_active=True)

    specialist_stats = []
    for specialist in specialists:
        if specialist.role == 'programmer':
            specialist_orders = orders_for_spec.filter(assigned_programmer=specialist)
            hours_field = 'programmer_hours'
        elif specialist.role == 'marketer':
            specialist_orders = orders_for_spec.filter(assigned_marketer=specialist)
            hours_field = 'marketer_hours'
        else:
            specialist_orders = orders_for_spec.filter(assigned_smm=specialist)
            hours_field = 'smm_hours'

        total_orders_spec = specialist_orders.count()
        completed_orders_spec = specialist_orders.filter(status='completed').count()
        total_hours = specialist_orders.aggregate(total=Sum(hours_field))['total'] or 0
        total_revenue_spec = specialist_orders.filter(status='completed').aggregate(total=Sum('total_price'))['total'] or 0
        avg_check = total_revenue_spec / completed_orders_spec if completed_orders_spec > 0 else 0

        specialist_stats.append({
            'name': specialist.get_full_name() or specialist.username,
            'role': specialist.role,
            'role_display': dict(User.ROLE_CHOICES).get(specialist.role, specialist.role),
            'total_orders': total_orders_spec,
            'completed_orders': completed_orders_spec,
            'total_hours': total_hours,
            'total_revenue': total_revenue_spec,
            'avg_check': avg_check,
        })

    # Сортировка специалистов
    if sort_spec == 'total_orders':
        specialist_stats.sort(key=lambda x: x['total_orders'], reverse=True)
    elif sort_spec == 'completed_orders':
        specialist_stats.sort(key=lambda x: x['completed_orders'], reverse=True)
    elif sort_spec == 'total_revenue':
        specialist_stats.sort(key=lambda x: x['total_revenue'], reverse=True)
    elif sort_spec == 'total_hours':
        specialist_stats.sort(key=lambda x: x['total_hours'], reverse=True)
    else:
        specialist_stats.sort(key=lambda x: x['total_orders'], reverse=True)

    # --- 3. Данные для вкладки "Услуги" (из popular_services) ---
    date_from_serv = request.GET.get('date_from_serv')
    date_to_serv = request.GET.get('date_to_serv')
    
    orders_for_services = Order.objects.all()
    if date_from_serv:
        orders_for_services = orders_for_services.filter(created_at__date__gte=date_from_serv)
    if date_to_serv:
        orders_for_services = orders_for_services.filter(created_at__date__lte=date_to_serv)

    from services.models import Service
    services_stats = {}
    for order in orders_for_services:
        for item in order.items.all():
            for service in item.package.available_services.all():
                if service.name not in services_stats:
                    services_stats[service.name] = {'count': 0, 'revenue': 0, 'price': service.price}
                services_stats[service.name]['count'] += item.quantity
                services_stats[service.name]['revenue'] += float(service.price) * item.quantity

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

    # Получаем активную вкладку
    active_tab = request.GET.get('active_tab', 'orders')

    context = {
        # Для вкладки "Заказы"
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
        'active_tab': active_tab,
        # Для вкладки "Специалисты"
        'specialists': specialist_stats,
        'role_filter': role_filter,
        'date_from_spec': date_from_spec,
        'date_to_spec': date_to_spec,
        'sort_spec': sort_spec,
        # Для вкладки "Услуги"
        'top_services': top_services,
        'date_from_serv': date_from_serv,
        'date_to_serv': date_to_serv,
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
def specialists_rating(request):
    """Рейтинг специалистов (программисты, маркетологи, SMM) с фильтрами и сортировкой"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    # Получаем параметры фильтрации
    role_filter = request.GET.get('role', '')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sort_by = request.GET.get('sort', '-total_orders')
    
    # Базовый queryset заказов
    orders = Order.objects.all()
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Специалисты
    if role_filter:
        specialists = User.objects.filter(role=role_filter, is_active=True)
    else:
        specialists = User.objects.filter(role__in=['programmer', 'marketer', 'smm'], is_active=True)
    
    specialist_stats = []
    
    for specialist in specialists:
        if specialist.role == 'programmer':
            specialist_orders = orders.filter(assigned_programmer=specialist)
            hours_field = 'programmer_hours'
        elif specialist.role == 'marketer':
            specialist_orders = orders.filter(assigned_marketer=specialist)
            hours_field = 'marketer_hours'
        else:
            specialist_orders = orders.filter(assigned_smm=specialist)
            hours_field = 'smm_hours'
        
        total_orders = specialist_orders.count()
        completed_orders = specialist_orders.filter(status='completed').count()
        total_hours = specialist_orders.aggregate(total=Sum(hours_field))['total'] or 0
        total_revenue = specialist_orders.filter(status='completed').aggregate(total=Sum('total_price'))['total'] or 0
        avg_check = total_revenue / completed_orders if completed_orders > 0 else 0
        
        specialist_stats.append({
            'id': specialist.id,
            'name': specialist.get_full_name() or specialist.username,
            'role': specialist.role,
            'role_display': dict(User.ROLE_CHOICES).get(specialist.role, specialist.role),
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'total_hours': total_hours,
            'total_revenue': total_revenue,
            'avg_check': avg_check,
        })
    
    # Сортировка
    if sort_by == 'total_orders':
        specialist_stats.sort(key=lambda x: x['total_orders'], reverse=True)
    elif sort_by == 'completed_orders':
        specialist_stats.sort(key=lambda x: x['completed_orders'], reverse=True)
    elif sort_by == 'total_revenue':
        specialist_stats.sort(key=lambda x: x['total_revenue'], reverse=True)
    elif sort_by == 'total_hours':
        specialist_stats.sort(key=lambda x: x['total_hours'], reverse=True)
    elif sort_by == 'avg_check':
        specialist_stats.sort(key=lambda x: x['avg_check'], reverse=True)
    else:
        specialist_stats.sort(key=lambda x: x['total_orders'], reverse=True)
    
    context = {
        'specialists': specialist_stats,
        'role_filter': role_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
    }
    
    return render(request, 'orders/specialists_rating.html', context)