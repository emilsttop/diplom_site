from django.urls import path
from . import views

urlpatterns = [
    path('my-orders/', views.my_orders, name='my_orders'),
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/update-status/<int:order_id>/', views.manager_update_order_status, name='manager_update_status'),
path('manager/analytics/', views.manager_analytics, name='manager_analytics'),
]