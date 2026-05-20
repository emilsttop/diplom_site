from django.urls import path
from . import views

urlpatterns = [
    path('api/messages/<int:order_id>/', views.get_messages, name='get_messages'),
    path('api/send/<int:order_id>/', views.send_message, name='send_message'),
    path('api/unread_count/', views.get_unread_count, name='get_unread_count'),
    path('api/specialist/messages/<int:order_id>/<int:specialist_id>/', views.get_specialist_messages, name='get_specialist_messages'),
    path('api/specialist/send/<int:order_id>/<int:specialist_id>/', views.send_specialist_message, name='send_specialist_message'),
    path('api/specialist/unread/<int:order_id>/<int:specialist_id>/', views.get_specialist_unread_status, name='get_specialist_unread_status'),
    path('api/manager/specialist/unread/', views.get_manager_specialist_unread_count, name='get_manager_specialist_unread_count'),  # ← ДОБАВИТЬ
    path('specialist/chat/<int:order_id>/<int:specialist_id>/', views.specialist_chat_page, name='specialist_chat_page'),
    path('manager/specialist/chat/<int:order_id>/<int:specialist_id>/', views.manager_specialist_chat_page, name='manager_specialist_chat_page'),
]