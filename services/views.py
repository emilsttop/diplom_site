from django.shortcuts import render
from .models import ServicePackage

def catalog(request):
    packages = ServicePackage.objects.all()
    return render(request, 'services/catalog.html', {'packages': packages})