from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('services.urls')),           # главная и каталог
    path('cart/', include('cart.urls')),         # корзина
    path('accounts/', include('accounts.urls')), # регистрация, вход, профиль
    path('orders/', include('orders.urls')),     # заказы, панель менеджера
    path('chat/', include('chat.urls')),         # чат
]