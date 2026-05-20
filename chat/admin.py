from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import ChatMessage, SpecialistChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'sender', 'get_receiver', 'message_preview', 'created_at', 'is_read', 'is_manager_only', 'edit_link')
    list_filter = ('is_read', 'is_manager_only', 'created_at', 'sender__role')
    search_fields = ('message', 'order__id', 'sender__username')
    date_hierarchy = 'created_at'
    list_editable = ('is_read', 'is_manager_only')
    
    # Убираем created_at из fieldsets (оно не редактируется)
    fieldsets = (
        ('Информация о сообщении', {
            'fields': ('order', 'sender', 'message')
        }),
        ('Статус', {
            'fields': ('is_read', 'is_manager_only')
        }),
    )
    
    readonly_fields = ('created_at',)  # Показываем, но не даём редактировать
    
    def get_receiver(self, obj):
        if obj.sender.role == 'client':
            return obj.order.assigned_manager
        else:
            return obj.order.client
    get_receiver.short_description = 'Получатель'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Сообщение'
    
    def edit_link(self, obj):
        url = reverse('admin:chat_chatmessage_change', args=[obj.id])
        return format_html('<a href="{}">✏️ Редактировать</a>', url)
    edit_link.short_description = 'Действие'


@admin.register(SpecialistChatMessage)
class SpecialistChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'sender', 'receiver', 'message_preview', 'created_at', 'is_read', 'edit_link')
    list_filter = ('is_read', 'created_at', 'sender__role', 'receiver__role')
    search_fields = ('message', 'order__id', 'sender__username', 'receiver__username')
    date_hierarchy = 'created_at'
    list_editable = ('is_read',)
    
    # Убираем created_at из fieldsets
    fieldsets = (
        ('Информация о сообщении', {
            'fields': ('order', 'sender', 'receiver', 'message')
        }),
        ('Статус', {
            'fields': ('is_read',)
        }),
    )
    
    readonly_fields = ('created_at',)  # Показываем, но не даём редактировать
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Сообщение'
    
    def edit_link(self, obj):
        url = reverse('admin:chat_specialistchatmessage_change', args=[obj.id])
        return format_html('<a href="{}">✏️ Редактировать</a>', url)
    edit_link.short_description = 'Действие'