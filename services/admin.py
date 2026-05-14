from django.contrib import admin
from .models import Service, ServicePackage

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_services', 'max_services', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    filter_horizontal = ('available_services',)
    ordering = ('sort_order',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'icon', 'available_services')
        }),
        ('Настройки', {
            'fields': ('min_services', 'max_services', 'is_active', 'sort_order')
        }),
    )