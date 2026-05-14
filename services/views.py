from django.shortcuts import render
from .models import ServicePackage
from django.shortcuts import get_object_or_404

def home(request):
    """Главная страница"""
    return render(request, 'services/home.html')

def catalog(request):
    packages = ServicePackage.objects.all()
    return render(request, 'services/catalog.html', {'packages': packages})

def package_detail(request, package_id):
    package = get_object_or_404(ServicePackage, id=package_id, is_active=True)
    return render(request, 'services/package_detail.html', {'package': package})