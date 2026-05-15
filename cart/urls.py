from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('add/<int:package_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:package_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:package_id>/', views.update_cart, name='update_cart'),
path('checkout/', views.checkout, name='checkout'),
path('add-with-services/', views.add_with_services, name='add_with_services'),
path('remove/<str:item_key>/', views.remove_from_cart, name='remove_from_cart'),
path('clear/', views.clear_cart, name='clear_cart'),
]