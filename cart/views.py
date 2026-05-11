from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from services.models import ServicePackage
from orders.models import Order, OrderItem
from decimal import Decimal
from orders.utils import assign_manager_to_order
from django.http import JsonResponse

@login_required
def cart_view(request):
    """Просмотр корзины"""
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for package_id, quantity in cart.items():
        package = get_object_or_404(ServicePackage, id=package_id)
        subtotal = package.price * quantity
        total += subtotal
        cart_items.append({
            'package': package,
            'quantity': quantity,
            'subtotal': subtotal,
        })
    
    return render(request, 'cart/cart.html', {
        'cart_items': cart_items,
        'total': total,
    })

@login_required
def add_to_cart(request, package_id):
    """Добавление пакета в корзину (поддерживает AJAX)"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        package_id_str = str(package_id)
        
        if package_id_str in cart:
            cart[package_id_str] += 1
        else:
            cart[package_id_str] = 1
        
        request.session['cart'] = cart
        
        # AJAX-запрос
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'cart_count': sum(cart.values())})
        
        return redirect('catalog')
    
    # GET-запрос (перенаправление)
    return redirect('catalog')

@login_required
def remove_from_cart(request, package_id):
    """Удаление пакета из корзины"""
    cart = request.session.get('cart', {})
    package_id_str = str(package_id)
    
    if package_id_str in cart:
        del cart[package_id_str]
    
    request.session['cart'] = cart
    return redirect('cart')

@login_required
def update_cart(request, package_id):
    """Обновление количества в корзине"""
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
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart')
    
    # Создаём заказ
    order = Order.objects.create(
        client=request.user,
        total_price=0,
        status='new'
    )
    
    total = Decimal('0')
    for package_id, quantity in cart.items():
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
    
    order.total_price = total
    order.save()
    
    # 🆕 Автоматически назначаем менеджера
    assign_manager_to_order(order)
    
    # Очищаем корзину
    request.session['cart'] = {}
    
    return redirect('profile')