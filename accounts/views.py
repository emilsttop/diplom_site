from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .forms import RegistrationForm
from orders.models import Order
from users.models import User

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Восстанавливаем отложенные услуги
            pending_package_id = request.session.pop('pending_package_id', None)
            pending_service_ids = request.session.pop('pending_service_ids', None)
            
            if pending_package_id and pending_service_ids:
                import json
                from services.models import Service, ServicePackage
                
                cart = request.session.get('cart', {})
                package_key = f"package_{pending_package_id}"
                
                service_ids_list = json.loads(pending_service_ids)
                services = Service.objects.filter(id__in=service_ids_list)
                
                if services.exists():
                    total_price = sum(s.price for s in services)
                    cart[package_key] = {
                        'package_name': ServicePackage.objects.get(id=pending_package_id).name,
                        'service_ids': service_ids_list,
                        'service_names': [s.name for s in services],
                        'services': [{
                            'name': s.name,
                            'price': float(s.price),
                            'programmer_hours': float(s.programmer_hours),
                            'marketer_hours': float(s.marketer_hours),
                            'smm_hours': float(s.smm_hours),
                        } for s in services],
                        'total_price': float(total_price),
                    }
                    request.session['cart'] = cart
            
            # Редирект в зависимости от роли
            if user.role in ['manager', 'admin']:
                return redirect('manager_dashboard')
            elif user.role in ['programmer', 'marketer', 'smm']:
                return redirect('specialist_dashboard')
            else:
                return redirect('catalog')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Восстанавливаем отложенные услуги (если есть)
            pending_package_id = request.session.pop('pending_package_id', None)
            pending_service_ids = request.session.pop('pending_service_ids', None)
            
            if pending_package_id and pending_service_ids:
                import json
                from services.models import Service, ServicePackage
                
                cart = request.session.get('cart', {})
                package_key = f"package_{pending_package_id}"
                
                service_ids_list = json.loads(pending_service_ids)
                services = Service.objects.filter(id__in=service_ids_list)
                
                if services.exists():
                    total_price = sum(s.price for s in services)
                    cart[package_key] = {
                        'package_name': ServicePackage.objects.get(id=pending_package_id).name,
                        'service_ids': service_ids_list,
                        'service_names': [s.name for s in services],
                        'services': [{
                            'name': s.name,
                            'price': float(s.price),
                            'programmer_hours': float(s.programmer_hours),
                            'marketer_hours': float(s.marketer_hours),
                            'smm_hours': float(s.smm_hours),
                        } for s in services],
                        'total_price': float(total_price),
                    }
                    request.session['cart'] = cart
            
            # Редирект в зависимости от роли
            if user.role in ['manager', 'admin']:
                return redirect('manager_dashboard')
            elif user.role in ['programmer', 'marketer', 'smm']:
                return redirect('specialist_dashboard')
            else:
                return redirect('catalog')
        else:
            return render(request, 'accounts/login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'accounts/login.html')

def user_logout(request):
    logout(request)
    return redirect('catalog')

@login_required
def profile(request):
    # Если пользователь менеджер или админ — отправляем в панель менеджера
    if request.user.role in ['manager', 'admin']:
        return redirect('manager_dashboard')
    
    # Если пользователь специалист (программист, маркетолог, SMM) — отправляем в его панель
    if request.user.role in ['programmer', 'marketer', 'smm']:
        return redirect('specialist_dashboard')
    
    # Для клиента показываем личный кабинет
    orders = Order.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'accounts/profile.html', {'orders': orders})

@login_required
def specialist_dashboard(request):
    if request.user.role not in ['programmer', 'marketer', 'smm']:
        return redirect('catalog')

    user = request.user
    role = user.role

    # Получаем фильтры из GET-параметров
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', 'week')
    chart_type = request.GET.get('chart_type', 'all')  # all, completed, cancelled

    # Определяем поле часов и фильтр в зависимости от роли
    if role == 'programmer':
        hours_field = 'programmer_hours'
        orders_filter = Q(assigned_programmer=user)
        role_display = 'Программист'
    elif role == 'marketer':
        hours_field = 'marketer_hours'
        orders_filter = Q(assigned_marketer=user)
        role_display = 'Маркетолог'
    else:  # smm
        hours_field = 'smm_hours'
        orders_filter = Q(assigned_smm=user)
        role_display = 'SMM-менеджер'

    # Базовый запрос заказов специалиста
    base_orders = Order.objects.filter(orders_filter)

    # Применяем фильтры по дате
    if date_from:
        base_orders = base_orders.filter(created_at__date__gte=date_from)
    if date_to:
        base_orders = base_orders.filter(created_at__date__lte=date_to)

        # ========== ФИЛЬТРАЦИЯ ДЛЯ ГРАФИКА И СПИСКА В ЗАВИСИМОСТИ ОТ chart_type ==========
    if chart_type == 'completed':
        filtered_orders = base_orders.filter(status='completed')
    elif chart_type == 'cancelled':
        filtered_orders = base_orders.filter(status='cancelled')
    elif chart_type == 'new':
        filtered_orders = base_orders.filter(status='new')
    else:  # 'all'
        filtered_orders = base_orders

    # Общая статистика (часы только по активным заказам, не отменённым)
    hours_queryset = base_orders.exclude(status='cancelled')
    total_hours = hours_queryset.aggregate(total=Sum(hours_field))['total'] or 0
    
    # Статистика по статусам (для карточек сверху)
    completed_orders_count = base_orders.filter(status='completed').count()
    cancelled_orders_count = base_orders.filter(status='cancelled').count()
    processing_orders_count = base_orders.exclude(status='completed').exclude(status='cancelled').count()

    # Данные для графика (используем filtered_orders)
    chart_data = []
    today = timezone.now().date()

    if period == 'day':
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            day_orders = filtered_orders.filter(created_at__date=day).count()
            chart_data.append({'period': day.strftime('%d.%m'), 'count': day_orders})

    elif period == 'week':
        for i in range(11, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * i)
            week_end = week_start + timedelta(days=6)
            week_orders = filtered_orders.filter(
                created_at__date__gte=week_start,
                created_at__date__lte=week_end
            ).count()
            chart_data.append({'period': f'{week_start.strftime("%d.%m")}-{week_end.strftime("%d.%m")}', 'count': week_orders})

    else:  # month
        for i in range(11, -1, -1):
            month = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            month_orders = filtered_orders.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).count()
            chart_data.append({'period': month_start.strftime('%b %Y'), 'count': month_orders})

    # ========== СПИСОК ЗАКАЗОВ (используем ТЕ ЖЕ filtered_orders, что и для графика) ==========
    orders_list = filtered_orders.order_by('-created_at')

        # Название для графика
    if chart_type == 'completed':
        chart_title = 'Выполненные заказы'
    elif chart_type == 'cancelled':
        chart_title = 'Отменённые заказы'
    elif chart_type == 'new':
        chart_title = 'Новые заказы'
    else:
        chart_title = 'Полученные заказы'

    context = {
        'role': role,
        'role_display': role_display,
        'orders': orders_list,
        'total_hours': total_hours,
        'completed_orders_count': completed_orders_count,
        'cancelled_orders_count': cancelled_orders_count,
        'processing_orders_count': processing_orders_count,
        'chart_data': chart_data,
        'chart_title': chart_title,
        'chart_type': chart_type,
        'date_from': date_from,
        'date_to': date_to,
        'period': period,
    }

    return render(request, 'accounts/specialist_dashboard.html', context)