from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Order, OrderItem
from .utils import assign_manager_to_order
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
    """Аналитика с вкладками: личная и общая"""
    if request.user.role not in ['manager', 'admin']:
        return redirect('catalog')
    
    # Личная аналитика
    personal_orders = Order.objects.filter(assigned_manager=request.user)
    
    personal_stats = {
        'total_orders': personal_orders.count(),
        'total_revenue': personal_orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'new': personal_orders.filter(status='new').count(),
        'processing': personal_orders.filter(status='processing').count(),
        'completed': personal_orders.filter(status='completed').count(),
        'cancelled': personal_orders.filter(status='cancelled').count(),
    }
    
    today = timezone.now().date()
    personal_orders_by_month = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = personal_orders.filter(created_at__range=(day_start, day_end)).count()
        personal_orders_by_month.append({'date': day.strftime('%d.%m'), 'count': count})
    
    personal_top_clients = personal_orders.filter(status='completed').values('client__username').annotate(
        total_spent=Sum('total_price'),
        orders_count=Count('id')
    ).order_by('-total_spent')[:5]
    
    # Общая аналитика
    all_orders = Order.objects.all()
    
    company_stats = {
        'total_orders': all_orders.count(),
        'total_revenue': all_orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'new': all_orders.filter(status='new').count(),
        'processing': all_orders.filter(status='processing').count(),
        'completed': all_orders.filter(status='completed').count(),
        'cancelled': all_orders.filter(status='cancelled').count(),
    }
    
    company_orders_by_month = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = all_orders.filter(created_at__range=(day_start, day_end)).count()
        company_orders_by_month.append({'date': day.strftime('%d.%m'), 'count': count})
    
    company_top_clients = all_orders.filter(status='completed').values('client__username').annotate(
        total_spent=Sum('total_price'),
        orders_count=Count('id')
    ).order_by('-total_spent')[:5]
    
    from services.models import ServicePackage
    popular_services = []
    for package in ServicePackage.objects.all():
        order_count = all_orders.filter(items__package=package).count()
        popular_services.append({'name': package.name, 'orders_count': order_count})
    popular_services = sorted(popular_services, key=lambda x: x['orders_count'], reverse=True)[:5]
    
    managers_stats = []
    for manager in User.objects.filter(role='manager', is_active=True):
        manager_orders = Order.objects.filter(assigned_manager=manager)
        managers_stats.append({
            'name': manager.get_full_name() or manager.username,
            'orders_count': manager_orders.count(),
            'revenue': manager_orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        })
    managers_stats.sort(key=lambda x: x['revenue'], reverse=True)
    
    context = {
        'personal_stats': personal_stats,
        'personal_orders_by_month': personal_orders_by_month,
        'personal_top_clients': personal_top_clients,
        'company_stats': company_stats,
        'company_orders_by_month': company_orders_by_month,
        'company_top_clients': company_top_clients,
        'popular_services': popular_services,
        'managers_stats': managers_stats,
    }
    
    return render(request, 'orders/manager_analytics.html', context)

@login_required
def download_contract(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.user.role == 'client' and order.client != request.user:
        return redirect('catalog')
    if request.user.role not in ['manager', 'admin', 'client']:
        return redirect('catalog')
    return generate_contract(order)

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

from django.http import FileResponse
import os
from django.conf import settings

@login_required
def download_contract(request, order_id):
    """Скачать готовый договор (DOCX)"""
    # Путь к файлу договора
    file_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'Договор на оказание рекламных услуг.docx')
    
    if not os.path.exists(file_path):
        return HttpResponse("Файл договора не найден", status=404)
    
    return FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')