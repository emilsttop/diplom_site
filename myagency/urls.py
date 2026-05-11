from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('services.urls')),
    path('cart/', include('cart.urls')),
    path('accounts/', include('accounts.urls')),  # ← должно быть ПЕРЕД orders
    path('orders/', include('orders.urls')),
    path('chat/', include('chat.urls')),
]