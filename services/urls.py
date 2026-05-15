from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<int:package_id>/', views.package_detail, name='package_detail'),
    path('custom-package/<int:package_id>/', views.custom_package_builder, name='custom_package_builder'),
]