from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'total_price', 'status', 'region', 'created_at', 'assigned_manager')
    list_filter = ('status', 'region', 'created_at', 'assigned_manager')
    search_fields = ('id', 'client__username', 'client__email', 'region')
    readonly_fields = ('services_data', 'programmer_hours', 'marketer_hours', 'smm_hours')
    list_editable = ('status', 'region', 'created_at')  # ← добавили created_at
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('client', 'status', 'total_price', 'region', 'created_at')
        }),
        ('Назначения', {
            'fields': ('assigned_manager', 'assigned_programmer', 'assigned_marketer', 'assigned_smm')
        }),
        ('Технические данные', {
            'fields': ('services_data', 'programmer_hours', 'marketer_hours', 'smm_hours'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client', 'assigned_manager')