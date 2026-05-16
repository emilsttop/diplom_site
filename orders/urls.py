from django.urls import path
from . import views

urlpatterns = [
    path('my-orders/', views.my_orders, name='my_orders'),
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/update-status/<int:order_id>/', views.manager_update_order_status, name='manager_update_status'),
    path('manager/analytics/', views.manager_analytics, name='manager_analytics'),
    path('manager/chat/<int:order_id>/', views.manager_chat, name='manager_chat'),
    path('contract/download/<int:order_id>/', views.download_contract, name='download_contract'),
    path('reassign/<int:order_id>/', views.reassign_order, name='reassign_order'),
    path('popular-services/', views.popular_services, name='popular_services'),
    path('manager-rating/', views.manager_rating, name='manager_rating'),
]