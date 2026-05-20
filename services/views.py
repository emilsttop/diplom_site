from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import ServicePackage, Service
from orders.utils import is_specialist_available


def home(request):
    """Главная страница"""
    return render(request, 'services/home.html')


def catalog(request):
    """Каталог услуг с предупреждением о загрузке специалистов (без блокировки)"""
    packages = ServicePackage.objects.all()
    
    for package in packages:
        programmer_hours = sum(s.programmer_hours for s in package.available_services.all())
        marketer_hours = sum(s.marketer_hours for s in package.available_services.all())
        smm_hours = sum(s.smm_hours for s in package.available_services.all())
        
        # Проверяем доступность, но не блокируем
        package.programmer_available = is_specialist_available('programmer', programmer_hours)
        package.marketer_available = is_specialist_available('marketer', marketer_hours)
        package.smm_available = is_specialist_available('smm', smm_hours)
        
        # Если какой-то специалист перегружен — показываем предупреждение
        package.warning = not (package.programmer_available and 
                               package.marketer_available and 
                               package.smm_available)
        package.available = True  # всегда доступен
    
    return render(request, 'services/catalog.html', {'packages': packages})


def package_detail(request, package_id):
    """Детальная страница пакета услуг (включая конструктор)"""
    package = get_object_or_404(ServicePackage, id=package_id, is_active=True)
    return render(request, 'services/package_detail.html', {'package': package})