from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import ServicePackage, CustomService

def home(request):
    """Главная страница"""
    return render(request, 'services/home.html')

def catalog(request):
    packages = ServicePackage.objects.all()
    return render(request, 'services/catalog.html', {'packages': packages})

def package_detail(request, package_id):
    package = get_object_or_404(ServicePackage, id=package_id, is_active=True)
    return render(request, 'services/package_detail.html', {'package': package})

@login_required
def custom_package_builder(request, package_id):
    package = get_object_or_404(ServicePackage, id=package_id)
    
    if request.method == 'POST':
        # Удаляем старые услуги пользователя для этого пакета
        CustomService.objects.filter(user=request.user, package=package).delete()
        
        # Получаем данные из формы
        service_names = request.POST.getlist('service_name[]')
        service_prices = request.POST.getlist('service_price[]')
        
        # Фильтруем пустые
        services_data = []
        total_price = Decimal('0')
        
        for name, price in zip(service_names, service_prices):
            if name.strip() and price:
                try:
                    price_dec = Decimal(str(price))
                    services_data.append({'name': name.strip(), 'price': float(price_dec)})
                    total_price += price_dec
                except:
                    pass
        
        # Проверка на минимальное количество услуг
        if len(services_data) < package.min_services:
            messages.error(request, f'Минимум {package.min_services} услуг. Добавлено: {len(services_data)}')
            return redirect('custom_package_builder', package_id=package_id)
        
        # Сохраняем услуги в БД
        for service in services_data:
            CustomService.objects.create(
                user=request.user,
                package=package,
                name=service['name'],
                price=Decimal(str(service['price']))
            )
        
        # Добавляем в корзину
        cart = request.session.get('cart', {})
        cart_key = f'custom_{package_id}_{request.user.id}'
        cart[cart_key] = {
            'type': 'custom',
            'package_name': package.name,
            'services': services_data,
            'total_price': float(total_price)
        }
        request.session['cart'] = cart
        
        messages.success(request, '✅ Ваш пакет услуг добавлен в корзину!')
        return redirect('cart')
    
    existing_services = CustomService.objects.filter(user=request.user, package=package)
    return render(request, 'services/custom_package_builder.html', {
        'package': package,
        'existing_services': existing_services,
    })