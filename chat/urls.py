from django.urls import path
from . import views

urlpatterns = [
    path('api/messages/<int:order_id>/', views.get_messages, name='get_messages'),
    path('api/send/<int:order_id>/', views.send_message, name='send_message'),
    path('api/unread-count/', views.get_unread_count, name='unread_count'),
]