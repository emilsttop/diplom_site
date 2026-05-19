import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from services.models import ServicePackage, Service
from orders.models import Order, OrderItem
from orders.utils import assign_manager_to_order, assign_specialist, is_specialist_available


@login_required
def cart_view(request):
    """Просмотр корзины"""
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for key, item in cart.items():
        # Формат с выбранными услугами (package_...)
        if isinstance(item, dict) and 'package_name' in item:
            cart_items.append({
                'type': 'package',
                'package_name': item.get('package_name'),
                'service_names': item.get('service_names', []),
                'total_price': item.get('total_price', 0),
                'key': key,
            })
            total += item.get('total_price', 0)
        # Старый формат (числовой ключ)
        elif str(key).isdigit():
            cart_items.append({
                'type': 'simple',
                'package_id': int(key),
                'quantity': item,
                'key': key,
            })
            try:
                package = ServicePackage.objects.get(id=int(key))
                total += package.price * item
            except:
                pass
    
    return render(request, 'cart/cart.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def add_to_cart(request, package_id):
    """Добавление пакета в корзину (старый формат)"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        package_id_str = str(package_id)
        
        if package_id_str in cart:
            cart[package_id_str] += 1
        else:
            cart[package_id_str] = 1
        
        request.session['cart'] = cart
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'cart_count': sum(cart.values())})
        
        return redirect('catalog')
    
    return redirect('catalog')


@login_required
def remove_from_cart(request, item_key):
    """Удаление элемента из корзины по ключу"""
    cart = request.session.get('cart', {})
    if item_key in cart:
        del cart[item_key]
    request.session['cart'] = cart
    return redirect('cart')


@login_required
def update_cart(request, package_id):
    """Обновление количества в корзине (старый формат)"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        cart = request.session.get('cart', {})
        package_id_str = str(package_id)
        
        if quantity > 0:
            cart[package_id_str] = quantity
        else:
            cart.pop(package_id_str, None)
        
        request.session['cart'] = cart
    
    return redirect('cart')


@login_required
def add_with_services(request):
    """Добавление пакета с выбранными услугами (включая комментарий)"""
    
    if not request.user.is_authenticated:
        request.session['pending_package_id'] = request.POST.get('package_id')
        request.session['pending_service_ids'] = request.POST.get('service_ids')
        request.session['pending_comment'] = request.POST.get('comment', '')
        return redirect('register')
    
    if request.method == 'POST':
        package_id = request.POST.get('package_id')
        service_ids = json.loads(request.POST.get('service_ids', '[]'))
        comment = request.POST.get('comment', '')
        
        if not service_ids:
            return JsonResponse({'error': 'Не выбрано ни одной услуги'}, status=400)
        
        package = get_object_or_404(ServicePackage, id=package_id)
        services = Service.objects.filter(id__in=service_ids)
        
        if services.count() < package.min_services:
            return JsonResponse({'error': f'Минимум {package.min_services} услуг'}, status=400)
        
        # ===== ПРОВЕРКА НА ДУБЛИРОВАНИЕ УСЛУГ С КОРЗИНОЙ =====
        cart = request.session.get('cart', {})
        existing_service_ids = set()
        
        # Собираем все service_ids из уже существующих пакетов в корзине
        for key, item in cart.items():
            if key.startswith('package_') and isinstance(item, dict):
                existing_service_ids.update(item.get('service_ids', []))
        
        # Проверяем, нет ли уже выбранных услуг в корзине
        for service_id in service_ids:
            if int(service_id) in existing_service_ids:
                return JsonResponse({'error': f'Услуга "{Service.objects.get(id=service_id).name}" уже добавлена из другого пакета'}, status=400)
        # ====================================================
        
        # Считаем часы
        programmer_hours = sum(float(s.programmer_hours) for s in services)
        marketer_hours = sum(float(s.marketer_hours) for s in services)
        smm_hours = sum(float(s.smm_hours) for s in services)
        
        # Проверяем доступность специалистов
        from orders.utils import is_specialist_available
        if not is_specialist_available('programmer', programmer_hours):
            return JsonResponse({'error': 'Нет свободных программистов'}, status=400)
        if not is_specialist_available('marketer', marketer_hours):
            return JsonResponse({'error': 'Нет свободных маркетологов'}, status=400)
        if not is_specialist_available('smm', smm_hours):
            return JsonResponse({'error': 'Нет свободных SMM-менеджеров'}, status=400)
        
        total_price = sum(s.price for s in services)
        
        package_key = f"package_{package_id}"
        
        cart[package_key] = {
            'package_name': package.name,
            'service_ids': service_ids,
            'service_names': [s.name for s in services],
            'services': [{
                'name': s.name,
                'price': float(s.price),
                'programmer_hours': float(s.programmer_hours),
                'marketer_hours': float(s.marketer_hours),
                'smm_hours': float(s.smm_hours),
            } for s in services],
            'total_price': float(total_price),
            'comment': comment,  # ← сохраняем комментарий
        }
        request.session['cart'] = cart
        
        return JsonResponse({'success': True, 'total_price': float(total_price)})
    
    return JsonResponse({'error': 'Метод не разрешён'}, status=405)


@login_required
def checkout(request):
    cart = request.session.get('cart', {})

    # Получаем регион из GET-параметра
    region = request.GET.get('region')
    
    print("=== ОФОРМЛЕНИЕ ЗАКАЗА ===")
    print("Корзина:", cart)
    
    if not cart:
        return redirect('cart')
    
    # Создаём заказ
    order = Order.objects.create(
        client=request.user,
        total_price=0,
        status='new',
        region=region,
        created_at=timezone.now(),
        comment=request.POST.get('comment', '')  # ← добавляем текущую дату
    )
    
    total = Decimal('0')
    services_items = []
    
    for key, item in cart.items():
        print(f"Обработка ключа: {key}, тип: {type(key)}")
        print(f"Значение: {item}")
        
        # Формат 1: ключ начинается с 'package_' (кастомный пакет)
        if key.startswith('package_') and isinstance(item, dict):
            item_total = Decimal(str(item.get('total_price', 0)))
            total += item_total
            
            # Суммируем часы специалистов из каждой услуги
            for service in item.get('services', []):
                order.programmer_hours += Decimal(str(service.get('programmer_hours', 0)))
                order.marketer_hours += Decimal(str(service.get('marketer_hours', 0)))
                order.smm_hours += Decimal(str(service.get('smm_hours', 0)))
            
            services_items.append({
                'type': 'custom',
                'package_name': item.get('package_name', 'Конструктор'),
                'services': item.get('services', []),
                'total_price': float(item_total)
            })
            print(f"  -> Кастомный пакет (package_), сумма: {item_total}")
        
        # Формат 2: словарь с ключом 'services' (альтернативный кастомный)
        elif isinstance(item, dict) and 'services' in item:
            item_total = Decimal(str(item.get('total_price', 0)))
            total += item_total
            
            # Суммируем часы специалистов
            for service in item.get('services', []):
                order.programmer_hours += Decimal(str(service.get('programmer_hours', 0)))
                order.marketer_hours += Decimal(str(service.get('marketer_hours', 0)))
                order.smm_hours += Decimal(str(service.get('smm_hours', 0)))
            
            services_items.append({
                'type': 'custom',
                'package_name': item.get('package_name', 'Конструктор'),
                'services': item.get('services', []),
                'total_price': float(item_total)
            })
            print(f"  -> Кастомный пакет (с services), сумма: {item_total}")
        
        # Формат 3: ключ — это число (ID пакета), значение — количество
        elif str(key).isdigit():
            try:
                package_id = int(key)
                quantity = int(item) if isinstance(item, (int, str)) else 1
                package = ServicePackage.objects.get(id=package_id)
                price = package.price
                item_total = price * quantity
                total += item_total
                
                OrderItem.objects.create(
                    order=order,
                    package=package,
                    quantity=quantity,
                    price=price
                )
                
                # Суммируем часы специалистов
                order.programmer_hours += Decimal(str(package.programmer_hours)) * quantity
                order.marketer_hours += Decimal(str(package.marketer_hours)) * quantity
                order.smm_hours += Decimal(str(package.smm_hours)) * quantity
                
                services_items.append({
                    'type': 'package',
                    'package_id': package.id,
                    'package_name': package.name,
                    'quantity': quantity,
                    'price': float(price),
                    'total': float(item_total)
                })
                print(f"  -> Обычный пакет: {package.name} x{quantity} = {item_total}")
            except ServicePackage.DoesNotExist:
                print(f"  -> Ошибка: пакет {key} не найден")
                continue
        
        # Формат 4: другое (неизвестно)
        else:
            print(f"  -> Неизвестный формат, пропускаем: {type(item)}")
    
    order.total_price = total
    order.services_data = {'items': services_items}
    order.save()
    
    print(f"Итого: {total} ₽")
    print(f"services_data: {order.services_data}")
    print(f"Часы: П={order.programmer_hours}, М={order.marketer_hours}, SMM={order.smm_hours}")
    
    # Назначаем специалистов
    if order.programmer_hours > 0:
        order.assigned_programmer = assign_specialist('programmer', order.programmer_hours, order.id)
    if order.marketer_hours > 0:
        order.assigned_marketer = assign_specialist('marketer', order.marketer_hours, order.id)
    if order.smm_hours > 0:
        order.assigned_smm = assign_specialist('smm', order.smm_hours, order.id)
    order.save()
    
    # Назначаем менеджера
    assign_manager_to_order(order)
    
    # Очищаем корзину
    request.session['cart'] = {}
    
    return redirect('profile')


@login_required
def clear_cart(request):
    """Очищает корзину текущего пользователя"""
    if request.method == 'POST':
        request.session['cart'] = {}
        request.session.modified = True
        return JsonResponse({'success': True, 'message': 'Корзина очищена'})
    return JsonResponse({'error': 'Метод не разрешён'}, status=405)